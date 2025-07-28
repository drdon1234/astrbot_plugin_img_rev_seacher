from json import loads as json_loads
from pathlib import Path
from typing import Any, Optional, Union
from typing_extensions import override
from ..response_parser import TineyeResponse
from ..types import DomainInfo
from ..ext_tools import deep_get, read_file
from .base_req import BaseSearchReq


class Tineye(BaseSearchReq[TineyeResponse]):
    """
    TinEye搜索请求类
    
    用于与TinEye反向图像搜索服务交互，支持分页浏览和按域名过滤等功能
    """
    
    def __init__(self, base_url: str = "https://tineye.com", **request_kwargs: Any):
        """
        初始化TinEye搜索请求
        
        参数:
            base_url: TinEye API的基础URL
            **request_kwargs: 其他请求参数
        """
        super().__init__(base_url, **request_kwargs)

    async def _get_domains(self, query_hash: str) -> list[DomainInfo]:
        """
        获取搜索结果中的域名信息
        
        参数:
            query_hash: 搜索查询的哈希值
            
        返回:
            list[DomainInfo]: 域名信息列表
        """
        resp = await self._send_request(method="get", endpoint=f"api/v1/search/get_domains/{query_hash}")
        resp_json = json_loads(resp.text)
        return [DomainInfo.from_raw_data(domain_data) for domain_data in resp_json.get("domains", [])]

    async def _navigate_page(self, resp: TineyeResponse, offset: int) -> Optional[TineyeResponse]:
        """
        导航到指定偏移量的结果页面
        
        参数:
            resp: 当前的搜索响应对象
            offset: 页面偏移量，可以是正数或负数
            
        返回:
            Optional[TineyeResponse]: 新的搜索响应对象，如果页面不存在则返回None
        """
        next_page_number = resp.page_number + offset
        if next_page_number < 1 or next_page_number > resp.total_pages:
            return None
        api_url = resp.url.replace("search/", "api/v1/result_json/").replace(
            f"page={resp.page_number}", f"page={next_page_number}"
        )
        _resp = await self._send_request(method="get", url=api_url)
        resp_json = json_loads(_resp.text)
        resp_json.update({"status_code": _resp.status_code})
        return TineyeResponse(
            resp_json,
            _resp.url,
            resp.domains,
            next_page_number,
        )

    async def pre_page(self, resp: TineyeResponse) -> Optional[TineyeResponse]:
        """
        获取上一页搜索结果
        
        参数:
            resp: 当前的搜索响应对象
            
        返回:
            Optional[TineyeResponse]: 上一页的搜索响应对象，如果是第一页则返回None
        """
        return await self._navigate_page(resp, -1)

    async def next_page(self, resp: TineyeResponse) -> Optional[TineyeResponse]:
        """
        获取下一页搜索结果
        
        参数:
            resp: 当前的搜索响应对象
            
        返回:
            Optional[TineyeResponse]: 下一页的搜索响应对象，如果是最后一页则返回None
        """
        return await self._navigate_page(resp, 1)

    @override
    async def search(
        self,
        url: Optional[str] = None,
        file: Union[str, bytes, Path, None] = None,
        show_unavailable_domains: bool = False,
        domain: str = "",
        sort: str = "score",
        order: str = "desc",
        tags: str = "",
        **kwargs: Any,
    ) -> TineyeResponse:
        """
        执行TinEye图像搜索
        
        参数:
            url: 图像URL
            file: 本地文件内容
            show_unavailable_domains: 是否显示不可用的域名
            domain: 按域名过滤结果
            sort: 结果排序方式，可选值包括"score"、"size"、"date"等
            order: 排序顺序，可选值为"asc"或"desc"
            tags: 按标签过滤结果
            **kwargs: 其他搜索参数
            
        返回:
            TineyeResponse: 搜索响应对象
            
        异常:
            ValueError: 当未提供url或file参数时抛出
        """
        files: Optional[dict[str, Any]] = None
        params: dict[str, Any] = {
            "sort": sort,
            "order": order,
            "page": 1,
            "show_unavailable_domains": show_unavailable_domains or "",
            "tags": tags,
            "domain": domain,
        }
        params = {k: v for k, v in params.items() if v}
        if url:
            params["url"] = url
        elif file:
            files = {"image": read_file(file)}
        else:
            raise ValueError("Either 'url' or 'file' must be provided")
        resp = await self._send_request(
            method="post",
            endpoint="api/v1/result_json/",
            data=params,
            files=files,
        )
        resp_json = json_loads(resp.text)
        resp_json["status_code"] = resp.status_code
        _url = resp.url
        domains = []
        if query_hash := deep_get(resp_json, "query.key"):
            query_string = "&".join(f"{k}={v}" for k, v in params.items())
            _url = f"{self.base_url}/search/{query_hash}?{query_string}"
            domains = await self._get_domains(resp_json["query"]["hash"])
        return TineyeResponse(resp_json, _url, domains)
