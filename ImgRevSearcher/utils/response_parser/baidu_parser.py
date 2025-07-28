from typing import Any
from typing_extensions import override
from ..ext_tools import deep_get
from .base_parser import BaseResParser, BaseSearchResponse


class BaiDuItem(BaseResParser):
    """
    百度识图搜索结果项解析器
    
    解析单个搜索结果，提取标题、URL和缩略图等信息
    """
    
    def __init__(self, data: dict[str, Any], **kwargs: Any) -> None:
        """
        初始化百度识图结果项解析器
        
        参数:
            data: 原始结果数据
            **kwargs: 其他解析参数
        """
        super().__init__(data, **kwargs)

    @override
    def _parse_data(self, data: dict[str, Any], **kwargs: Any) -> None:
        """
        解析百度识图结果数据
        
        参数:
            data: 原始结果数据
            **kwargs: 其他解析参数
        """
        self.title: str = deep_get(data, "title[0]") or ""
        self.thumbnail: str = data.get("image_src") or data.get("thumbUrl") or ""
        self.url: str = data.get("url") or data.get("fromUrl") or ""


class BaiDuResponse(BaseSearchResponse[BaiDuItem]):
    """
    百度识图搜索响应解析器
    
    解析完整的百度识图API响应，包含相似图片和相同图片的搜索结果
    """
    
    def __init__(self, resp_data: dict[str, Any], resp_url: str, **kwargs: Any):
        """
        初始化百度识图响应解析器
        
        参数:
            resp_data: 原始响应数据
            resp_url: 响应URL
            **kwargs: 其他解析参数
        """
        super().__init__(resp_data, resp_url, **kwargs)

    @override
    def _parse_response(self, resp_data: dict[str, Any], **kwargs: Any) -> None:
        """
        解析百度识图响应数据
        
        参数:
            resp_data: 原始响应数据
            **kwargs: 其他解析参数
        """
        self.raw: list[BaiDuItem] = []
        self.exact_matches: list[BaiDuItem] = []
        if same_data := resp_data.get("same"):
            if "list" in same_data:
                self.exact_matches.extend(BaiDuItem(i) for i in same_data["list"] if "url" in i and "image_src" in i)
        if data_list := deep_get(resp_data, "data.list"):
            self.raw.extend([BaiDuItem(i) for i in data_list])
            
    def show_result(self) -> str:
        """
        生成可读的搜索结果文本
        
        返回:
            str: 格式化的搜索结果文本，包含相似结果和最佳匹配
        """
        lines = []
        if self.exact_matches:
            lines.extend(["最佳结果:", "-" * 50])
            for idx, item in enumerate(self.exact_matches, 1):
                lines.append(f"结果 #{idx}")
                lines.append(f"标题: {item.title}")
                lines.append(f"链接: {item.url}")
                lines.append("-" * 50)
        if self.raw:
            lines.extend(["相关结果:", "-" * 50])
            for idx, item in enumerate(self.raw, 1):
                lines.append(f"结果 #{idx}")
                lines.append(f"链接: {item.url}")
                lines.append("-" * 50)
        else:
            lines.append("无相关结果")
            

        return "\n".join(lines)
