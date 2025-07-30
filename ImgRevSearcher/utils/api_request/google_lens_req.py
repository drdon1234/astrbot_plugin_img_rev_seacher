from pathlib import Path
from typing import Any, Literal, Optional, Union
from pyquery import PyQuery
from typing_extensions import override
from ..response_parser import GoogleLensExactMatchesResponse, GoogleLensResponse
from ..network import RESP
from ..ext_tools import read_file
from .base_req import BaseSearchReq
from ..types import FileContent


VALID_SEARCH_TYPES = ["all", "products", "visual_matches", "exact_matches"]
SEARCH_TYPE_UDM = {
    "products": "37",
    "visual_matches": "44",
    "exact_matches": "48"
}


class GoogleLens(BaseSearchReq[Union[GoogleLensResponse, GoogleLensExactMatchesResponse]]):
    """
    Google Lens搜索请求类
    
    提供基于图像的搜索功能，支持多种搜索类型和过滤选项
    """
    
    def __init__(
        self,
        base_url: str = "https://lens.google.com",
        search_url: str = "https://www.google.com",
        search_type: Literal["all", "products", "visual_matches", "exact_matches"] = "all",
        q: Optional[str] = None,
        hl: str = "en",
        country: str = "US",
        max_results: int = 50,
        **request_kwargs: Any,
    ):
        """
        初始化Google Lens搜索请求
        
        参数:
            base_url: Google Lens API基础URL
            search_url: Google搜索基础URL
            search_type: 搜索类型，可选值为"all"、"products"、"visual_matches"或"exact_matches"
            q: 搜索查询词
            hl: 界面语言代码
            country: 国家/地区代码
            max_results: 最大结果数量
            **request_kwargs: 其他请求参数
            
        异常:
            ValueError: 当搜索类型无效、参数组合不兼容或max_results不是正整数时抛出
        """
        super().__init__(base_url, **request_kwargs)
        if search_type not in VALID_SEARCH_TYPES:
            raise ValueError(f"无效的search_type: {search_type}。必须是以下之一: {', '.join(VALID_SEARCH_TYPES)}")
        if search_type == "exact_matches" and q:
            raise ValueError("Query parameter 'q' is not applicable for 'exact_matches' search_type.")
        if max_results <= 0:
            raise ValueError("max_results must be a positive integer")
        self.search_url: str = search_url
        self.hl_param: str = f"{hl}-{country.upper()}"
        self.search_type: str = search_type
        self.q: Optional[str] = q
        self.max_results: int = max_results

    async def _perform_image_search(
        self,
        url: Optional[str] = None,
        file: FileContent = None,
        q: Optional[str] = None,
    ) -> RESP:
        """
        执行图像搜索请求
        
        参数:
            url: 图像URL
            file: 本地文件内容
            q: 搜索查询词
            
        返回:
            RESP: HTTP响应对象
            
        异常:
            ValueError: 当未提供url或file参数时抛出
        """
        params = {"hl": self.hl_param}
        if q and self.search_type != "exact_matches":
            params["q"] = q
        if file:
            endpoint = "v3/upload"
            filename = "image.jpg" if isinstance(file, bytes) else Path(file).name
            files = {"encoded_image": (filename, read_file(file), "image/jpeg")}
            resp = await self._send_request(
                method="post",
                endpoint=endpoint,
                params=params,
                files=files,
            )
        elif url:
            endpoint = "uploadbyurl"
            params["url"] = url
            resp = await self._send_request(
                method="post" if file else "get",
                endpoint=endpoint,
                params=params,
            )
        else:
            raise ValueError("Either 'url' or 'file' must be provided")
        dom = PyQuery(resp.text)
        exact_link = ""
        
        if self.search_type != "all" and self.search_type in SEARCH_TYPE_UDM:
            udm_value = SEARCH_TYPE_UDM[self.search_type]
            exact_link = dom(f'a[href*="udm={udm_value}"]').attr("href") or ""
            
        if exact_link:
            return await self._send_request(method="get", url=f"{self.search_url}{exact_link}")
        return resp

    @override
    async def search(
        self,
        url: Optional[str] = None,
        file: FileContent = None,
        q: Optional[str] = None,
        **kwargs: Any,
    ) -> Union[GoogleLensResponse, GoogleLensExactMatchesResponse]:
        """
        执行Google Lens搜索
        
        参数:
            url: 图像URL
            file: 本地文件内容
            q: 搜索查询词，对于exact_matches类型会被忽略
            **kwargs: 其他搜索参数
            
        返回:
            Union[GoogleLensResponse, GoogleLensExactMatchesResponse]: 根据搜索类型返回相应的响应对象
        """
        if q is not None and self.search_type == "exact_matches":
            q = None
        resp = await self._perform_image_search(url, file, q)
        if self.search_type == "exact_matches":
            response = GoogleLensExactMatchesResponse(resp.text, resp.url)
            response._parse_response(resp.text, resp_url=resp.url, max_results=self.max_results)
            return response
        else:
            response = GoogleLensResponse(resp.text, resp.url)
            response._parse_response(resp.text, resp_url=resp.url, max_results=self.max_results)
            return response
