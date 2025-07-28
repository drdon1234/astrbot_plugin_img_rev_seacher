from json import loads as json_loads
from pathlib import Path
from typing import Any, Optional, Union
from lxml.html import HTMLParser, fromstring
from pyquery import PyQuery
from typing_extensions import override
from ..response_parser import BaiDuResponse
from ..ext_tools import deep_get, read_file
from .base_req import BaseSearchReq


class BaiDu(BaseSearchReq[BaiDuResponse]):
    """
    百度识图搜索请求类
    
    用于与百度识图服务交互，获取相似图片和相同图片的搜索结果
    """
    
    def __init__(self, **request_kwargs: Any):
        """
        初始化百度识图搜索请求
        
        参数:
            **request_kwargs: 其他请求参数
        """
        base_url = "https://graph.baidu.com"
        super().__init__(base_url, **request_kwargs)

    @staticmethod
    def _extract_card_data(data: PyQuery) -> list[dict[str, Any]]:
        """
        从页面中提取卡片数据
        
        参数:
            data: PyQuery对象，包含页面HTML
            
        返回:
            list[dict[str, Any]]: 提取的卡片数据列表
        """
        for script in data("script").items():
            script_text = script.text()
            if script_text and "window.cardData" in script_text:
                start = script_text.find("[")
                end = script_text.rfind("]") + 1
                return json_loads(script_text[start:end])
        return []

    @override
    async def search(
        self,
        url: Optional[str] = None,
        file: Union[str, bytes, Path, None] = None,
        **kwargs: Any,
    ) -> BaiDuResponse:
        """
        执行百度识图搜索
        
        参数:
            url: 图像URL
            file: 本地文件内容
            **kwargs: 其他搜索参数
            
        返回:
            BaiDuResponse: 搜索响应对象
            
        异常:
            ValueError: 当未提供url或file参数时抛出
        """
        data = {"from": "pc"}
        if url:
            files = {"image": await self.download(url)}
        elif file:
            files = {"image": read_file(file)}
        else:
            raise ValueError("Either 'url' or 'file' must be provided")
        resp = await self._send_request(
            method="post",
            endpoint="upload",
            headers={"Acs-Token": ""},
            data=data,
            files=files,
        )
        data_url = deep_get(json_loads(resp.text), "data.url")
        if not data_url:
            return BaiDuResponse({}, resp.url)
        resp = await self._send_request(method="get", url=data_url)
        utf8_parser = HTMLParser(encoding="utf-8")
        data = PyQuery(fromstring(resp.text, parser=utf8_parser))
        card_data = self._extract_card_data(data)
        same_data = None
        for card in card_data:
            if card.get("cardName") == "noresult":
                return BaiDuResponse({}, data_url)
            if card.get("cardName") == "same":
                same_data = card["tplData"]
            if card.get("cardName") == "simipic":
                next_url = card["tplData"]["firstUrl"]
                resp = await self._send_request(method="get", url=next_url)
                resp_data = json_loads(resp.text)
                if same_data:
                    resp_data["same"] = same_data
                return BaiDuResponse(resp_data, data_url)
        return BaiDuResponse({}, data_url)
