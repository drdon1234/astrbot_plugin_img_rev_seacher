from typing import Any, Callable, Optional
from typing_extensions import override
from .base_parser import BaseResParser, BaseSearchResponse


class BingItem(BaseResParser):
    """
    Bing图像搜索基础结果项解析器
    
    解析单个搜索结果，提取标题、URL和缩略图等信息
    """
    
    def __init__(self, data: dict[str, Any], **kwargs: Any):
        """
        初始化Bing结果项解析器
        
        参数:
            data: 原始结果数据
            **kwargs: 其他解析参数
        """
        super().__init__(data, **kwargs)

    @override
    def _parse_data(self, data: dict[str, Any], **kwargs: Any) -> None:
        """
        解析Bing结果数据
        
        参数:
            data: 原始结果数据
            **kwargs: 其他解析参数
        """
        self.title: str = data.get("name", "")
        self.url: str = data.get("hostPageUrl", "")
        self.thumbnail: str = data.get("thumbnailUrl", "")
        self.image_url: str = data.get("contentUrl", "")


class RelatedSearchItem:
    """
    相关搜索项解析器
    
    解析相关搜索建议，包含文本和缩略图
    """
    
    def __init__(self, data: dict[str, Any]):
        """
        初始化相关搜索项解析器
        
        参数:
            data: 原始数据
        """
        self.text: str = data.get("text", "")
        self.thumbnail: str = data.get("thumbnail", {}).get("url", "")


class PagesIncludingItem:
    """
    包含页面项解析器
    
    解析包含该图像的网页信息
    """
    
    def __init__(self, data: dict[str, Any]):
        """
        初始化包含页面项解析器
        
        参数:
            data: 原始数据
        """
        self.name: str = data.get("name", "")
        self.thumbnail: str = data.get("thumbnailUrl", "")
        self.url: str = data.get("hostPageUrl", "")
        self.image_url: str = data.get("contentUrl", "")


class VisualSearchItem:
    """
    视觉搜索项解析器
    
    解析视觉相似的图像信息
    """
    
    def __init__(self, data: dict[str, Any]):
        """
        初始化视觉搜索项解析器
        
        参数:
            data: 原始数据
        """
        self.name: str = data.get("name", "")
        self.thumbnail: str = data.get("thumbnailUrl", "")
        self.url: str = data.get("hostPageUrl", "")
        self.image_url: str = data.get("contentUrl", "")


class Attraction:
    """
    景点信息解析器
    
    解析旅行相关的景点信息
    """
    
    def __init__(self, data: dict[str, Any]):
        """
        初始化景点信息解析器
        
        参数:
            data: 原始数据
        """
        self.url: str = data.get("attractionUrl", "")
        self.title: str = data.get("title", "")
        self.search_url: str = data.get("requeryUrl", "")
        self.interest_types: list[str] = data.get("interestTypes", [])


class TravelCard:
    """
    旅行卡片解析器
    
    解析旅行相关的卡片信息
    """
    
    def __init__(self, data: dict[str, Any]):
        """
        初始化旅行卡片解析器
        
        参数:
            data: 原始数据
        """
        self.card_type: str = data.get("cardType", "")
        self.title: str = data.get("title", "")
        self.url: str = data.get("clickUrl", "")
        self.image_url: str = data.get("image", "")
        self.image_source_url: str = data.get("imageSourceUrl", "")


class TravelInfo:
    """
    旅行信息解析器
    
    解析旅行相关的综合信息，包含目的地、景点和卡片等
    """
    
    def __init__(self, data: dict[str, Any]):
        """
        初始化旅行信息解析器
        
        参数:
            data: 原始数据
        """
        self.destination_name: str = data.get("destinationName", "")
        self.travel_guide_url: str = data.get("travelGuideUrl", "")
        self.attractions: list[Attraction] = [Attraction(x) for x in data.get("attractions", [])]
        self.travel_cards: list[TravelCard] = [TravelCard(x) for x in data.get("travelCards", [])]


class EntityItem:
    """
    实体信息解析器
    
    解析识别出的实体信息，如人物、地点等
    """
    
    def __init__(self, data: dict[str, Any]):
        """
        初始化实体信息解析器
        
        参数:
            data: 原始数据
        """
        self.name: str = data.get("name", "")
        self.thumbnail: str = data.get("image", {}).get("thumbnailUrl", "")
        self.description: str = data.get("description", "")
        self.profiles: list[dict[str, str]] = []
        if social_media := data.get("socialMediaInfo"):
            self.profiles = [
                {
                    "url": profile.get("profileUrl"),
                    "social_network": profile.get("socialNetwork"),
                }
                for profile in social_media.get("profiles", [])
            ]
        self.short_description: str = data.get("entityPresentationInfo", {}).get("entityTypeDisplayHint", "")


class BingResponse(BaseSearchResponse[BingItem]):
    """
    Bing图像搜索响应解析器
    
    解析完整的Bing图像搜索API响应，包含多种类型的搜索结果
    """
    
    def __init__(self, resp_data: dict[str, Any], resp_url: str, **kwargs: Any):
        """
        初始化Bing响应解析器
        
        参数:
            resp_data: 原始响应数据
            resp_url: 响应URL
            **kwargs: 其他解析参数
        """
        super().__init__(resp_data, resp_url, **kwargs)

    @override
    def _parse_response(self, resp_data: dict[str, Any], **kwargs: Any) -> None:
        """
        解析Bing响应数据
        
        参数:
            resp_data: 原始响应数据
            **kwargs: 其他解析参数
        """
        self.pages_including: list[PagesIncludingItem] = []
        self.visual_search: list[VisualSearchItem] = []
        self.related_searches: list[RelatedSearchItem] = []
        self.best_guess: Optional[str] = None
        self.travel: Optional[TravelInfo] = None
        self.entities: list[EntityItem] = []
        if tags := resp_data.get("tags"):
            for tag in tags:
                for action in tag.get("actions", []):
                    self._parse_action(action)

    def _parse_action(self, action: dict[str, Any]) -> None:
        """
        根据动作类型解析不同的结果数据
        
        参数:
            action: 动作数据
        """
        action_type: str = action.get("actionType", "")
        action_handlers: dict[str, Callable[[dict[str, Any]], None]] = {
            "PagesIncluding": self._handle_pages_including,
            "VisualSearch": self._handle_visual_search,
            "RelatedSearches": self._handle_related_searches,
            "BestRepresentativeQuery": self._handle_best_query,
            "Travel": self._handle_travel,
            "Entity": self._handle_entity,
        }
        if handler := action_handlers.get(action_type):
            handler(action)

    def _handle_pages_including(self, action: dict[str, Any]) -> None:
        """
        处理包含页面的动作数据
        
        参数:
            action: 动作数据
        """
        if value := action.get("data", {}).get("value"):
            self.pages_including.extend([PagesIncludingItem(val) for val in value])

    def _handle_visual_search(self, action: dict[str, Any]) -> None:
        """
        处理视觉搜索的动作数据
        
        参数:
            action: 动作数据
        """
        if value := action.get("data", {}).get("value"):
            self.visual_search.extend([VisualSearchItem(val) for val in value])

    def _handle_related_searches(self, action: dict[str, Any]) -> None:
        """
        处理相关搜索的动作数据
        
        参数:
            action: 动作数据
        """
        if value := action.get("data", {}).get("value"):
            self.related_searches.extend([RelatedSearchItem(val) for val in value])

    def _handle_best_query(self, action: dict[str, Any]) -> None:
        """
        处理最佳查询的动作数据
        
        参数:
            action: 动作数据
        """
        self.best_guess = action.get("displayName")

    def _handle_travel(self, action: dict[str, Any]) -> None:
        """
        处理旅行信息的动作数据
        
        参数:
            action: 动作数据
        """
        self.travel = TravelInfo(action.get("data", {}))

    def _handle_entity(self, action: dict[str, Any]) -> None:
        """
        处理实体信息的动作数据
        
        参数:
            action: 动作数据
        """
        if data := action.get("data"):
            self.entities.append(EntityItem(data))
            
    def show_result(self) -> str:
        """
        生成可读的搜索结果文本
        
        返回:
            str: 格式化的搜索结果文本
        """
        lines = ["-" * 50]
        combined = (self.pages_including or []) + (self.visual_search or [])
        if combined:
            for idx, item in enumerate(combined, 1):
                lines.append(f"结果 #{idx}")
                lines.append(f"标题：{item.name}")
                lines.append(f"页面链接：{item.url}")
                lines.append(f"图片链接：{item.image_url}")
                lines.append("-" * 50)
        if self.best_guess:
            lines.append(f"最佳结果：{self.best_guess}")
            lines.append("-" * 50)
        return '\n'.join(lines)
