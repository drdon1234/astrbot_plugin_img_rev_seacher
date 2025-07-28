import re
from base64 import b64encode
from json import dumps as json_dumps
from json import loads as json_loads
from pathlib import Path
from typing import Any, Optional, Union
from urllib.parse import quote_plus
from typing_extensions import override
from ..response_parser import BingResponse
from ..ext_tools import read_file
from .base_req import BaseSearchReq


class Bing(BaseSearchReq[BingResponse]):
    """
    Bing图像搜索请求类
    
    用于与Bing图像搜索服务交互，获取相似图片和视觉匹配等结果
    """
    
    def __init__(self, **request_kwargs: Any):
        """
        初始化Bing图像搜索请求
        
        参数:
            **request_kwargs: 其他请求参数
        """
        base_url = "https://www.bing.com"
        super().__init__(base_url, **request_kwargs)

    async def _upload_image(self, file: Union[str, bytes, Path]) -> tuple[str, str]:
        """
        上传图像到Bing服务器
        
        参数:
            file: 本地文件内容
            
        返回:
            tuple[str, str]: 包含BCID和响应URL的元组
            
        异常:
            ValueError: 当无法从响应中提取BCID时抛出
        """
        endpoint = "images/search?view=detailv2&iss=sbiupload"
        image_base64 = b64encode(read_file(file)).decode("utf-8")
        files = {
            "cbir": "sbi",
            "imageBin": image_base64,
        }
        resp = await self._send_request(method="post", endpoint=endpoint, files=files)
        if match := re.search(r"(bcid_[A-Za-z0-9-.]+)", resp.text):
            return match[1], str(resp.url)
        raise ValueError("BCID not found on page.")

    async def _get_insights(self, bcid: Optional[str] = None, image_url: Optional[str] = None) -> dict[str, Any]:
        """
        获取图像的洞察信息
        
        参数:
            bcid: 图像的BCID标识符
            image_url: 图像URL
            
        返回:
            dict[str, Any]: 包含图像洞察信息的JSON响应
        """
        endpoint = "images/api/custom/knowledge"
        params: dict[str, Any] = {
            "rshighlight": "true",
            "textDecorations": "true",
            "internalFeatures": "similarproducts,share",
            "nbl": "1",
            "FORM": "SBIHMP",
            "safeSearch": "off",
            "mkt": "en-us",
            "setLang": "en-us",
            "iss": "sbi",
            "IID": "idpins",
            "SFX": "1",
        }
        if image_url:
            referer = (
                f"{self.base_url}/images/search?"
                f"view=detailv2&iss=sbi&FORM=SBIHMP&sbisrc=UrlPaste"
                f"&q=imgurl:{quote_plus(image_url)}&idpbck=1"
            )
            image_info = {"imageInfo": {"url": image_url, "source": "Url"}}
        else:
            params["insightsToken"] = bcid
            referer = f"{self.base_url}/images/search?insightsToken={bcid}"
            image_info = {"imageInfo": {"imageInsightsToken": bcid, "source": "Gallery"}}
            if self.client:
                self.client.cookies.clear()
        headers = {"Referer": referer}
        files = {
            "knowledgeRequest": (
                None,
                json_dumps(image_info),
                "application/json",
            )
        }
        resp = await self._send_request(method="post", endpoint=endpoint, headers=headers, params=params, files=files)
        return json_loads(resp.text)

    @override
    async def search(
        self,
        url: Optional[str] = None,
        file: Union[str, bytes, Path, None] = None,
        **kwargs: Any,
    ) -> BingResponse:
        """
        执行Bing图像搜索
        
        参数:
            url: 图像URL
            file: 本地文件内容
            **kwargs: 其他搜索参数
            
        返回:
            BingResponse: 搜索响应对象
            
        异常:
            ValueError: 当未提供url或file参数时抛出
        """
        if url:
            resp_url = (
                f"{self.base_url}/images/search?"
                f"view=detailv2&iss=sbi&FORM=SBIHMP&sbisrc=UrlPaste"
                f"&q=imgurl:{url}&idpbck=1"
            )
            resp_json = await self._get_insights(image_url=url)
        elif file:
            bcid, resp_url = await self._upload_image(file)
            resp_json = await self._get_insights(bcid=bcid)
        else:
            raise ValueError("Either 'url' or 'file' must be provided")
        return BingResponse(resp_json, resp_url)
