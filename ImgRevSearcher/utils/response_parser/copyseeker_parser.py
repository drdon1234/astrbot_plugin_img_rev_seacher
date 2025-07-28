from typing import Any, Optional
from typing_extensions import override
from .base_parser import BaseResParser, BaseSearchResponse


class CopyseekerItem(BaseResParser):
    """
    Copyseeker搜索结果项解析器
    
    解析单个匹配结果，提取URL、标题和缩略图等信息
    """
    
    def __init__(self, data: dict[str, Any], **kwargs: Any):
        """
        初始化Copyseeker结果项解析器
        
        参数:
            data: 原始结果数据
            **kwargs: 其他解析参数
        """
        super().__init__(data, **kwargs)

    @override
    def _parse_data(self, data: dict[str, Any], **kwargs: Any) -> None:
        """
        解析Copyseeker结果数据
        
        参数:
            data: 原始结果数据
            **kwargs: 其他解析参数
        """
        self.url: str = data["url"]
        self.title: str = data["title"]
        self.thumbnail: str = data.get("mainImage", "")
        self.thumbnail_list: list[str] = data.get("otherImages", [])
        self.website_rank: float = data.get("rank", 0.0)


class CopyseekerResponse(BaseSearchResponse[CopyseekerItem]):
    """
    Copyseeker搜索响应解析器
    
    解析完整的Copyseeker API响应，包含匹配结果、相似图片和EXIF信息等
    """
    
    def __init__(self, resp_data: dict[str, Any], resp_url: str, **kwargs: Any) -> None:
        """
        初始化Copyseeker响应解析器
        
        参数:
            resp_data: 原始响应数据
            resp_url: 响应URL
            **kwargs: 其他解析参数
        """
        super().__init__(resp_data, resp_url, **kwargs)

    @override
    def _parse_response(self, resp_data: dict[str, Any], **kwargs: Any) -> None:
        """
        解析Copyseeker响应数据
        
        参数:
            resp_data: 原始响应数据
            **kwargs: 其他解析参数
        """
        self.id: str = resp_data["id"]
        self.image_url: str = resp_data["imageUrl"]
        self.best_guess_label: Optional[str] = resp_data.get("bestGuessLabel")
        self.entities: Optional[str] = resp_data.get("entities")
        self.total: int = resp_data["totalLinksFound"]
        self.exif: dict[str, Any] = resp_data.get("exif", {})
        self.raw: list[CopyseekerItem] = [CopyseekerItem(page) for page in resp_data.get("pages", [])]
        self.similar_image_urls: list[str] = resp_data.get("visuallySimilarImages", [])
        
    def show_result(self) -> str:
        """
        生成可读的搜索结果文本
        
        返回:
            str: 格式化的搜索结果文本
        """
        lines = []
        if self.raw:
            lines.append(f"匹配图源：{self.raw[0].url}")
        else:
            lines.append("匹配图源：无")
            
        lines.append("相似图片：")
        for i, url in enumerate(self.similar_image_urls, 1):
            lines.extend([f"  #{i} {url}", "-" * 50])
        return '\n'.join(lines)
