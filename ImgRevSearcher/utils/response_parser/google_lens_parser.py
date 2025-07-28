import re
from ast import literal_eval
from typing import Any, Optional
from urllib.parse import urlparse
from pyquery import PyQuery
from typing_extensions import override
from ..ext_tools import parse_html
from .base_parser import BaseResParser, BaseSearchResponse


def get_site_name(url: Optional[str]) -> str:
    """
    从URL中提取网站名称
    
    参数:
        url: 网页URL
        
    返回:
        str: 提取的网站域名，不包含www前缀
    """
    if not url:
        return ""
    parsed_url = urlparse(url)
    return parsed_url.netloc.replace("www.", "") if parsed_url.netloc else ""


def parse_image_size(html: PyQuery) -> Optional[str]:
    """
    从HTML中解析图像尺寸信息
    
    参数:
        html: PyQuery对象
        
    返回:
        Optional[str]: 图像尺寸字符串，如"800x600"，未找到则返回None
    """
    return next((span.text() for span in html("div.oYQBg.Zn52Me > span").items() 
                if span.text() and "x" in span.text()), None)


def extract_ldi_images(script_text: str, image_url_map: dict[str, str]) -> None:
    """
    从脚本文本中提取延迟加载的图像URL
    
    参数:
        script_text: JavaScript脚本文本
        image_url_map: 用于存储图像ID到URL映射的字典
    """
    ldi_match = re.search(r"google\.ldi\s*=\s*({[^}]+})", script_text)
    if not ldi_match:
        return
    try:
        ldi_dict = literal_eval(ldi_match[1])
        for key, value in ldi_dict.items():
            if key.startswith("dimg_"):
                image_url_map[key] = value.replace("\\u003d", "=").replace("\\u0026", "&")
    except (SyntaxError, ValueError) as e:
        print(f"Error parsing google.ldi JSON: {e}")


def extract_base64_images(script_text: str, base64_image_map: dict[str, str]) -> None:
    """
    从脚本文本中提取Base64编码的图像数据
    
    参数:
        script_text: JavaScript脚本文本
        base64_image_map: 用于存储图像ID到Base64数据映射的字典
    """
    if "_setImagesSrc" not in script_text:
        return
    image_ids_match = re.search(r"var ii=\[([^]]*)];", script_text)
    base64_match = re.search(r"var s='(data:image/[^;]+;base64,[^']+)';", script_text)
    if not (image_ids_match and base64_match):
        return
    image_ids_str = image_ids_match[1]
    image_ids = [img_id.strip().strip("'") for img_id in image_ids_str.split(",") if img_id.strip()]
    base64_str = base64_match[1]
    if image_ids and base64_str:
        for img_id in image_ids:
            base64_image_map[img_id] = base64_str


def extract_image_maps(html: PyQuery) -> tuple[dict[str, str], dict[str, str]]:
    """
    从HTML中提取所有图像映射
    
    参数:
        html: PyQuery对象
        
    返回:
        tuple[dict[str, str], dict[str, str]]: 包含图像URL映射和Base64图像映射的元组
    """
    base64_image_map: dict[str, str] = {}
    image_url_map: dict[str, str] = {}
    for script_element in html("script[nonce]"):
        if script_text := PyQuery(script_element).text():
            extract_ldi_images(script_text, image_url_map)
            extract_base64_images(script_text, base64_image_map)
    return image_url_map, base64_image_map


class GoogleLensBaseItem(BaseResParser):
    """
    Google Lens基础结果项解析器
    
    所有Google Lens结果项的基类，提供图像URL提取等共享功能
    """
    
    def __init__(
        self,
        data: PyQuery,
        image_url_map: dict[str, str],
        base64_image_map: dict[str, str],
        **kwargs: Any,
    ):
        """
        初始化Google Lens基础结果项解析器
        
        参数:
            data: PyQuery对象，包含结果项HTML
            image_url_map: 图像ID到URL的映射
            base64_image_map: 图像ID到Base64数据的映射
            **kwargs: 其他解析参数
        """
        self.image_url_map: dict[str, str] = image_url_map
        self.base64_image_map: dict[str, str] = base64_image_map
        super().__init__(data, **kwargs)

    @override
    def _parse_data(self, data: PyQuery, **kwargs: Any) -> None:
        """
        解析结果数据
        
        参数:
            data: PyQuery对象
            **kwargs: 其他解析参数
        """
        pass

    def _extract_image_url(self, image_element: PyQuery) -> str:
        """
        从图像元素中提取URL
        
        参数:
            image_element: 包含图像的PyQuery元素
            
        返回:
            str: 图像URL或Base64数据
        """
        if not image_element:
            return ""
        
        image_id = image_element.attr("data-iid") or image_element.attr("id")
        if image_id:
            return self.image_url_map.get(image_id, "") or self.base64_image_map.get(image_id, "")
            
        return image_element.attr("data-src") or image_element.attr("src") or ""


class GoogleLensItem(GoogleLensBaseItem):
    """
    Google Lens搜索结果项解析器
    
    解析常规搜索结果中的单个项目
    """
    
    def __init__(
        self,
        data: PyQuery,
        image_url_map: dict[str, str],
        base64_image_map: dict[str, str],
        **kwargs: Any,
    ):
        """
        初始化Google Lens结果项解析器
        
        参数:
            data: PyQuery对象，包含结果项HTML
            image_url_map: 图像ID到URL的映射
            base64_image_map: 图像ID到Base64数据的映射
            **kwargs: 其他解析参数
        """
        super().__init__(data, image_url_map, base64_image_map, **kwargs)

    @override
    def _parse_data(self, data: PyQuery, **kwargs: Any) -> None:
        """
        解析Google Lens结果数据
        
        参数:
            data: PyQuery对象
            **kwargs: 其他解析参数
        """
        link_element = data("a.LBcIee")
        title_element = data("a.LBcIee .Yt787")
        site_name_element = data("a.LBcIee .R8BTeb.q8U8x.LJEGod.du278d.i0Rdmd")
        image_element = data(".gdOPf.q07dbf.uhHOwf.ez24Df img")
        self.url: str = link_element.attr("href") if link_element else ""
        self.title: str = title_element.text() if title_element else ""
        if site_name_element:
            self.site_name: str = site_name_element.text()
        else:
            self.site_name = get_site_name(self.url)
        self.thumbnail: str = self._extract_image_url(image_element)


class GoogleLensRelatedSearchItem(GoogleLensBaseItem):
    """
    Google Lens相关搜索项解析器
    
    解析相关搜索建议中的单个项目
    """
    
    def __init__(
        self,
        data: PyQuery,
        image_url_map: dict[str, str],
        base64_image_map: dict[str, str],
        **kwargs: Any,
    ):
        """
        初始化Google Lens相关搜索项解析器
        
        参数:
            data: PyQuery对象，包含相关搜索项HTML
            image_url_map: 图像ID到URL的映射
            base64_image_map: 图像ID到Base64数据的映射
            **kwargs: 其他解析参数
        """
        super().__init__(data, image_url_map, base64_image_map, **kwargs)

    @override
    def _parse_data(self, data: PyQuery, **kwargs: Any) -> None:
        """
        解析Google Lens相关搜索项数据
        
        参数:
            data: PyQuery对象
            **kwargs: 其他解析参数
        """
        url_el = data("a.Kg0xqe")
        image_element = data("img")
        if url_el and url_el.attr("href"):
            self.url: str = f"https://www.google.com{url_el.attr('href')}"
        self.title: str = data(".I9S4yc").text()
        self.thumbnail: str = self._extract_image_url(image_element)


class GoogleLensResponse(BaseSearchResponse[GoogleLensItem]):
    """
    Google Lens搜索响应解析器
    
    解析完整的Google Lens API响应，包含常规搜索结果和相关搜索建议
    """
    
    def __init__(self, resp_data: str, resp_url: str, **kwargs: Any):
        """
        初始化Google Lens响应解析器
        
        参数:
            resp_data: 原始HTML响应数据
            resp_url: 响应URL
            **kwargs: 其他解析参数
        """
        super().__init__(resp_data, resp_url, **kwargs)

    def _parse_search_items(
        self, html: PyQuery, image_url_map: dict[str, str], base64_image_map: dict[str, str], max_results: int = 0
    ) -> None:
        """
        解析搜索结果项
        
        参数:
            html: PyQuery对象，包含完整HTML
            image_url_map: 图像ID到URL的映射
            base64_image_map: 图像ID到Base64数据的映射
            max_results: 最大结果数量，0表示不限制
        """
        items_elements = html(".vEWxFf.RCxtQc.my5z3d")
        for idx, el in enumerate(items_elements):
            if max_results > 0 and idx >= max_results:
                break
            item = GoogleLensItem(PyQuery(el), image_url_map, base64_image_map)
            self.raw.append(item)

    def _parse_related_searches(
        self, html: PyQuery, image_url_map: dict[str, str], base64_image_map: dict[str, str]
    ) -> None:
        """
        解析相关搜索项
        
        参数:
            html: PyQuery对象，包含完整HTML
            image_url_map: 图像ID到URL的映射
            base64_image_map: 图像ID到Base64数据的映射
        """
        related_searches_elements = html(".Kg0xqe")
        for el in related_searches_elements:
            related_item = GoogleLensRelatedSearchItem(PyQuery(el), image_url_map, base64_image_map)
            self.related_searches.append(related_item)

    @override
    def _parse_response(self, resp_data: str, **kwargs: Any) -> None:
        """
        解析Google Lens响应数据
        
        参数:
            resp_data: 原始HTML响应数据
            **kwargs: 其他解析参数
        """
        html = parse_html(resp_data)
        self.origin: PyQuery = html
        self.url: str = kwargs.get("resp_url", "")
        self.raw: list[GoogleLensItem] = []
        self.related_searches: list[GoogleLensRelatedSearchItem] = []
        max_results = kwargs.get("max_results", 0)
        image_url_map, base64_image_map = extract_image_maps(html)
        self._parse_search_items(html, image_url_map, base64_image_map, max_results)
        self._parse_related_searches(html, image_url_map, base64_image_map)
        
    def show_result(self) -> str:
        """
        生成可读的搜索结果文本
        
        返回:
            str: 格式化的搜索结果文本
        """
        if self.raw:
            lines = ["搜索结果:", "-" * 50]
            for idx, item in enumerate(self.raw, 1):
                lines.append(f"结果 #{idx}")
                lines.append(f"标题: {item.title}")
                lines.append(f"链接: {item.url}")
                lines.append("-" * 50)
            return "\n".join(lines)
        return "未找到匹配结果"


class GoogleLensExactMatchesItem(GoogleLensBaseItem):
    """
    Google Lens精确匹配结果项解析器
    
    解析精确匹配搜索结果中的单个项目
    """
    
    def __init__(
        self,
        data: PyQuery,
        image_url_map: dict[str, str],
        base64_image_map: dict[str, str],
        **kwargs: Any,
    ):
        """
        初始化Google Lens精确匹配结果项解析器
        
        参数:
            data: PyQuery对象，包含结果项HTML
            image_url_map: 图像ID到URL的映射
            base64_image_map: 图像ID到Base64数据的映射
            **kwargs: 其他解析参数
        """
        super().__init__(data, image_url_map, base64_image_map, **kwargs)

    @override
    def _parse_data(self, data: PyQuery, **kwargs: Any) -> None:
        """
        解析Google Lens精确匹配结果数据
        
        参数:
            data: PyQuery对象
            **kwargs: 其他解析参数
        """
        link_element = data("a.ngTNl")
        title_element = data(".ZhosBf")
        image_element = data(".GmoL0c .zVq10e img")
        site_name_element = data(".XC18Gb .LbKnXb .xuPcX")
        info_div = data(".oYQBg.Zn52Me")
        self.url: str = link_element.attr("href") if link_element else ""
        self.title: str = title_element.text() if title_element else ""
        if site_name_element:
            self.site_name: str = site_name_element.text()
        else:
            self.site_name = get_site_name(self.url)
        self.size: Optional[str] = parse_image_size(info_div)
        self.thumbnail: str = self._extract_image_url(image_element)


class GoogleLensExactMatchesResponse(BaseSearchResponse[GoogleLensExactMatchesItem]):
    """
    Google Lens精确匹配响应解析器
    
    解析完整的Google Lens精确匹配API响应
    """
    
    def __init__(self, resp_data: str, resp_url: str, **kwargs: Any):
        """
        初始化Google Lens精确匹配响应解析器
        
        参数:
            resp_data: 原始HTML响应数据
            resp_url: 响应URL
            **kwargs: 其他解析参数
        """
        super().__init__(resp_data, resp_url, **kwargs)

    @staticmethod
    def _parse_search_items(
        html: PyQuery,
        image_url_map: dict[str, str],
        base64_image_map: dict[str, str],
        max_results: int = 0,
    ) -> list[GoogleLensExactMatchesItem]:
        """
        解析精确匹配搜索结果项
        
        参数:
            html: PyQuery对象，包含完整HTML
            image_url_map: 图像ID到URL的映射
            base64_image_map: 图像ID到Base64数据的映射
            max_results: 最大结果数量，0表示不限制
            
        返回:
            list[GoogleLensExactMatchesItem]: 精确匹配结果项列表
        """
        items = []
        items_elements = html(".YxbOwd")
        for idx, el in enumerate(items_elements):
            if max_results > 0 and idx >= max_results:
                break
            item = GoogleLensExactMatchesItem(PyQuery(el), image_url_map, base64_image_map)
            items.append(item)
        return items

    @override
    def _parse_response(self, resp_data: str, **kwargs: Any) -> None:
        """
        解析Google Lens精确匹配响应数据
        
        参数:
            resp_data: 原始HTML响应数据
            **kwargs: 其他解析参数
        """
        html = parse_html(resp_data)
        self.origin: PyQuery = html
        self.url: str = kwargs.get("resp_url", "")
        self.raw: list[GoogleLensExactMatchesItem] = []
        max_results = kwargs.get("max_results", 0)
        image_url_map, base64_image_map = extract_image_maps(html)
        self.raw = self._parse_search_items(html, image_url_map, base64_image_map, max_results)
        
    def show_result(self) -> str:
        """
        生成可读的搜索结果文本
        
        返回:
            str: 格式化的搜索结果文本
        """
        if self.raw:
            lines = ["精确匹配的结果:", "-" * 50]
            for idx, item in enumerate(self.raw, 1):
                lines.append(f"结果 #{idx}")
                lines.append(f"标题: {item.title}")
                lines.append(f"链接: {item.url}")
                lines.append("-" * 50)
            return "\n".join(lines)
        return "未找到精确匹配结果"
