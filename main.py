import asyncio
import io
import os
import re
import tempfile
import time
from typing import List
from pathlib import Path
import httpx
from PIL import Image, ImageDraw, ImageFont
from astrbot.api.event import AstrMessageEvent, filter
from astrbot.api.message_components import Image as AstrImage, Nodes, Node, Plain
from astrbot.api.star import Context, Star, register
from .ImgRevSearcher.model import BaseSearchModel

# 支持的所有图像搜索引擎
ALL_ENGINES = [
    "animetrace", "baidu", "bing", "copyseeker", "ehentai", "google", "saucenao", "tineye"
]

# 各引擎基础信息
ENGINE_INFO = {
    "animetrace": {"url": "https://www.animetrace.com/", "anime": True},
    "baidu": {"url": "https://graph.baidu.com/", "anime": False},
    "bing": {"url": "https://www.bing.com/images/search", "anime": False},
    "copyseeker": {"url": "https://copyseeker.net/", "anime": False},
    "ehentai": {"url": "https://e-hentai.org/", "anime": True},
    "google": {"url": "https://lens.google.com/", "anime": False},
    "saucenao": {"url": "https://saucenao.com/", "anime": True},
    "tineye": {"url": "https://tineye.com/search/", "anime": False}
}

# 主题配色
COLOR_THEME = {
    "bg": (255, 255, 255),
    "header_bg": (67, 99, 216),
    "header_text": (255, 255, 255),
    "table_header": (240, 242, 245),
    "cell_bg_even": (250, 250, 252),
    "cell_bg_odd": (255, 255, 255),
    "border": (180, 185, 195),
    "text": (50, 50, 50),
    "url": (41, 98, 255),
    "success": (76, 175, 80),
    "fail": (244, 67, 54),
    "shadow": (0, 0, 0, 30),
    "hint": (100, 100, 100)
}

def is_image_url(text: str) -> bool:
    """
    判断文本是否为图片URL（http开头，常见图片扩展名结尾）

    参数:
        text (str): 待检测文本

    返回:
        bool: 是图片则True，否则False

    异常:
        无
    """
    return bool(re.match(r"^https://.*\.(jpg|jpeg|png|gif|webp|bmp)$", text, re.IGNORECASE))

def split_text_by_length(text: str, max_length: int = 4000) -> List[str]:
    """
    按最大长度将长文本智能断行拆分，优先按50连字符切分

    参数:
        text (str): 待分割文本
        max_length (int): 每段最大长度

    返回:
        List[str]: 拆分碎片

    异常:
        无
    """
    if len(text) <= max_length:
        return [text]
    separator = "-" * 50
    result = []
    while text:
        if len(text) <= max_length:
            result.append(text)
            break
        cut_index = max_length
        separator_index = text.rfind(separator, 0, max_length)
        if separator_index != -1 and separator_index > max_length // 2:
            cut_index = separator_index + len(separator)
        result.append(text[:cut_index])
        text = text[cut_index:]
    return result

def get_img_urls(message) -> List[str]:
    """
    从消息对象中提取所有图片的URL

    参数:
        message: 消息体对象，可含message或raw_message属性

    返回:
        List[str]: 图片URL列表

    异常:
        无
    """
    img_urls = []
    for component_str in getattr(message, 'message', []):
        if "type='Image'" in str(component_str):
            url_match = re.search(r"url='([^']+)'", str(component_str))
            if url_match:
                img_urls.append(url_match.group(1))
    raw_message = getattr(message, 'raw_message', '')
    if isinstance(raw_message, dict) and "message" in raw_message:
        for msg_part in raw_message.get("message", []):
            if msg_part.get("type") == "image":
                data = msg_part.get("data", {})
                url = data.get("url", "")
                if url and url not in img_urls:
                    img_urls.append(url)
    return img_urls

def get_message_text(message) -> str:
    """
    提取消息对象中的文本内容（忽略图片和其他非文本消息段落）

    参数:
        message: 消息体对象

    返回:
        str: 提取到的文本内容（去首尾空格）

    异常:
        无
    """
    raw_message = getattr(message, 'raw_message', '')
    if isinstance(raw_message, str):
        return raw_message.strip()
    elif isinstance(raw_message, dict) and "message" in raw_message:
        texts = [
            msg_part.get("data", {}).get("text", "")
            for msg_part in raw_message.get("message", [])
            if msg_part.get("type") == "text"
        ]
        return " ".join(texts).strip()
    return ''


@register("astrbot_plugin_img_rev_searcher", "drdon1234", "以图搜图，找出处", "2.3")
class ImgRevSearcherPlugin(Star):
    """
    以图搜图插件主类

    实现图片及文本消息的识别、搜索入口流程控制与结果发送
    """

    def __init__(self, context: Context, config: dict):
        """
        初始化插件实例及配置

        参数:
            context: 机器人上下文对象
            config: 配置字典

        变量:
            client: HTTP异步客户端
            user_states: 用户状态字典
            cleanup_task: 用户超时定时清理协程
            available_engines: 实际启用的引擎列表
            search_model: 搜索执行模型
            state_handlers: 状态处理器方法字典

        返回:
            无

        异常:
            无
        """
        super().__init__(context)
        self.client = httpx.AsyncClient()
        self.user_states = {}
        self.cleanup_task = asyncio.create_task(self.cleanup_loop())
        available_apis_config = config.get("available_apis", {})
        self.available_engines = [e for e in ALL_ENGINES if available_apis_config.get(e, True)]
        self.search_model = BaseSearchModel(
            proxies=config.get("proxies", ""),
            timeout=60,
            default_params=config.get("default_params", {}),
            default_cookies=config.get("default_cookies", {}),
            auto_google_config=config.get("auto_google_cookie", {})
        )
        self.state_handlers = {
            "waiting_text_confirm": self._handle_waiting_text_confirm,
            "waiting_engine": self._handle_waiting_engine,
            "waiting_both": self._handle_waiting_both,
            "waiting_image": self._handle_waiting_image,
        }

    async def cleanup_loop(self):
        """
        定时清理超时无响应的用户状态数据

        异常:
            无（彻底失效的用户会被字典剔除）
        """
        while True:
            await asyncio.sleep(600)
            now = time.time()
            to_delete = [
                user_id for user_id, state in list(self.user_states.items())
                if now - state['timestamp'] > 30
            ]
            for user_id in to_delete:
                del self.user_states[user_id]

    async def terminate(self):
        """
        插件关闭时收尾操作：关闭http连接与定时清理任务

        异常:
            无
        """
        await self.client.aclose()
        if hasattr(self, 'cleanup_task'):
            self.cleanup_task.cancel()

    async def _download_img(self, url: str):
        """
        异步下载图片数据，转为BytesIO对象

        参数:
            url (str): 图片URL

        返回:
            io.BytesIO or None: 成功则为图片数据流，否则None

        异常:
            网络异常会吞掉，返回None
        """
        try:
            r = await self.client.get(url, timeout=15)
            if r.status_code == 200:
                return io.BytesIO(r.content)
        except Exception:
            pass
        return None

    async def get_imgs(self, img_urls: List[str]) -> List[io.BytesIO]:
        """
        批量并发下载多张图片

        参数:
            img_urls (List[str]): 目标URL列表

        返回:
            List[io.BytesIO]: 所有获取成功的图片流集合

        异常:
            无
        """
        if not img_urls:
            return []
        imgs = await asyncio.gather(*[self._download_img(url) for url in img_urls])
        return [img for img in imgs if img is not None]

    async def _send_image(self, event: AstrMessageEvent, content: bytes):
        """
        以临时文件方式向目标事件发送图片消息

        参数:
            event: 事件对象
            content: 图片二进制内容

        返回:
            yield消息发送结果

        异常:
            无
        """
        with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as temp_file:
            temp_file.write(content)
            temp_file_path = temp_file.name
        yield event.chain_result([AstrImage.fromFileSystem(temp_file_path)])
        if os.path.exists(temp_file_path):
            os.unlink(temp_file_path)

    async def _send_engine_intro(self, event: AstrMessageEvent):
        """
        绘制并发送引擎表格介绍图片，便于用户首次选择

        参数:
            event: 事件对象

        返回:
            yield发送图片

        异常:
            无
        """
        width = 800
        cell_height = 50
        header_height = 60
        title_height = 70
        table_height = header_height + cell_height * len(self.available_engines)
        height = title_height + table_height + 25
        border_width = 2
        
        def rounded_rectangle(draw, xy, radius, fill=None, outline=None, width=1):
            x1, y1, x2, y2 = xy
            diameter = 2 * radius
            draw.rectangle([x1 + radius, y1, x2 - radius, y2], fill=fill, outline=outline, width=width)
            draw.rectangle([x1, y1 + radius, x2, y2 - radius], fill=fill, outline=outline, width=width)
            draw.pieslice([x1, y1, x1 + diameter, y1 + diameter], 180, 270, fill=fill, outline=outline, width=width)
            draw.pieslice([x2 - diameter, y1, x2, y1 + diameter], 270, 360, fill=fill, outline=outline, width=width)
            draw.pieslice([x1, y2 - diameter, x1 + diameter, y2], 90, 180, fill=fill, outline=outline, width=width)
            draw.pieslice([x2 - diameter, y2 - diameter, x2, y2], 0, 90, fill=fill, outline=outline, width=width)

        img = Image.new('RGB', (width, height), COLOR_THEME["bg"])
        draw = ImageDraw.Draw(img)
        workspace_root = Path(__file__).parent
        try:
            font_path = str(workspace_root / "ImgRevSearcher/resource/font/arialuni.ttf")
            title_font = ImageFont.truetype(font_path, 24)
            header_font = ImageFont.truetype(font_path, 18)
            body_font = ImageFont.truetype(font_path, 16)
        except Exception:
            title_font = ImageFont.load_default()
            header_font = ImageFont.load_default()
            body_font = ImageFont.load_default()
        rounded_rectangle(draw, [20, 15, width - 20, title_height - 5], 10, fill=COLOR_THEME["header_bg"])
        title = "可用搜索引擎"
        title_width = draw.textlength(title, font=title_font) if hasattr(draw, 'textlength') else title_font.getsize(title)[0]
        title_x = (width - title_width) // 2
        draw.text((title_x, 25), title, font=title_font, fill=COLOR_THEME["header_text"])
        table_x = 20
        table_width = width - 40
        col_widths = [int(table_width * 0.20), int(table_width * 0.50), int(table_width * 0.30)]
        table_y = title_height + 10
        table_bottom = table_y + header_height + cell_height * len(self.available_engines)
        draw.rectangle([table_x, table_y, table_x + sum(col_widths), table_y + header_height], fill=COLOR_THEME["table_header"])
        y = table_y + header_height
        for idx, engine in enumerate(self.available_engines):
            if engine not in ENGINE_INFO:
                continue
            row_bg = COLOR_THEME["cell_bg_even"] if idx % 2 == 0 else COLOR_THEME["cell_bg_odd"]
            draw.rectangle([table_x, y, table_x + sum(col_widths), y + cell_height], fill=row_bg)
            y += cell_height
        headers = ["引擎", "网址", "二次元图片专用"]
        x = table_x
        for i, header in enumerate(headers):
            text_width = draw.textlength(header, font=header_font) if hasattr(draw, 'textlength') else header_font.getsize(header)[0]
            text_x = x + (col_widths[i] - text_width) // 2
            draw.text((text_x, table_y + (header_height - 18) // 2), header, font=header_font, fill=COLOR_THEME["text"])
            x += col_widths[i]
        y = table_y + header_height
        for idx, engine in enumerate(self.available_engines):
            if engine not in ENGINE_INFO:
                continue
            info = ENGINE_INFO[engine]
            x = table_x
            draw.text((x + 15, y + (cell_height - 16) // 2), engine, font=body_font, fill=COLOR_THEME["text"])
            x += col_widths[0]
            draw.text((x + 15, y + (cell_height - 16) // 2), info["url"], font=body_font, fill=COLOR_THEME["url"])
            x += col_widths[1]
            mark = "✓" if info["anime"] else "✗"
            mark_color = COLOR_THEME["success"] if info["anime"] else COLOR_THEME["fail"]
            mark_width = draw.textlength(mark, font=header_font) if hasattr(draw, 'textlength') else header_font.getsize(mark)[0]
            draw.text((x + (col_widths[2] - mark_width) // 2, y + (cell_height - 18) // 2), mark, font=header_font, fill=mark_color)
            y += cell_height
        draw.rectangle([table_x, table_y, table_x + sum(col_widths), table_bottom], outline=COLOR_THEME["border"], width=border_width)
        for i in range(1, len(self.available_engines) + 1):
            line_y = table_y + header_height + cell_height * i
            if i < len(self.available_engines):
                draw.line([(table_x, line_y), (table_x + sum(col_widths), line_y)], fill=COLOR_THEME["border"], width=border_width)
        draw.line([(table_x, table_y + header_height), (table_x + sum(col_widths), table_y + header_height)], fill=COLOR_THEME["border"], width=border_width)
        col_x = table_x
        for i in range(len(col_widths) - 1):
            col_x += col_widths[i]
            draw.line([(col_x, table_y), (col_x, table_bottom)], fill=COLOR_THEME["border"], width=border_width)
        with io.BytesIO() as output:
            img.save(output, format="JPEG", quality=85)
            output.seek(0)
            async for result in self._send_image(event, output.getvalue()):
                yield result

    async def _perform_search(self, event: AstrMessageEvent, engine: str, img_buffer: io.BytesIO):
        """
        调用模型执行图片反向搜索（含异常提示图渲染）

        参数:
            event: 消息事件对象
            engine: 引擎名称
            img_buffer: 图片二进制流

        返回:
            yield图片/提示

        异常:
            出错时生成错误提示图片
        """
        file_bytes = img_buffer.getvalue()
        result_text = await self.search_model.search(api=engine, file=file_bytes)
        img_buffer.seek(0)
        try:
            source_image = Image.open(img_buffer)
            result_img = self.search_model.draw_results(engine, result_text, source_image)
        except Exception as e:
            result_img = self.search_model.draw_error(engine, str(e))
        with io.BytesIO() as output:
            result_img.save(output, format="JPEG", quality=85)
            output.seek(0)
            async for result in self._send_image(event, output.getvalue()):
                yield result
        yield event.plain_result("需要文本格式的结果吗？回复\"是\"以获取，10秒内有效")
        user_id = event.get_sender_id()
        self.user_states[user_id] = {
            "step": "waiting_text_confirm",
            "timestamp": time.time(),
            "result_text": result_text
        }

    async def _send_engine_prompt(self, event: AstrMessageEvent, state: dict):
        """
        按状态发送引擎选择或图片上传提示

        参数:
            event: 当前事件
            state: 用户状态

        返回:
            yield文本或图片提示

        异常:
            无
        """
        if not self.available_engines:
            yield event.plain_result("当前没有可用的搜索引擎，请联系管理员在配置中启用至少一个引擎")
            return
        example_engine = self.available_engines[0]
        if not state.get('engine'):
            async for result in self._send_engine_intro(event):
                yield result
        if state.get('preloaded_img'):
            yield event.plain_result(f"图片已接收，请回复引擎名（如{example_engine}），30秒内有效")
        elif state.get('engine'):
            yield event.plain_result(f"已选择引擎: {state['engine']}，请发送图片或图片URL，30秒内有效")
        else:
            yield event.plain_result(f"请选择引擎（回复引擎名，如{example_engine}）并发送图片，30秒内有效")

    async def _handle_timeout(self, event: AstrMessageEvent, user_id: str):
        """
        响应超时操作，移除用户状态并提示取消

        参数:
            event: 消息事件
            user_id: 目标用户ID

        返回:
            yield文本提示

        异常:
            无
        """
        yield event.plain_result("等待超时，操作取消")
        if user_id in self.user_states:
            del self.user_states[user_id]
        event.stop_event()

    async def _handle_waiting_text_confirm(self, event: AstrMessageEvent, state: dict, user_id: str):
        """
        等待用户是否主动获取文本格式结果

        参数:
            event: 事件对象
            state: 用户状态
            user_id: 用户ID

        返回:
            yield文本消息

        异常:
            无
        """
        message_text = get_message_text(event.message_obj)
        if time.time() - state["timestamp"] > 10:
            del self.user_states[user_id]
            event.stop_event()
            return
        elif message_text.strip().lower() == "是":
            text_parts = split_text_by_length(state["result_text"])
            sender_name = "图片搜索bot"
            sender_id = event.get_self_id()
            try:
                sender_id = int(sender_id)
            except Exception:
                sender_id = 10000
            for i, part in enumerate(text_parts):
                node = Node(
                    name=sender_name,
                    uin=sender_id,
                    content=[Plain(f"[  搜索结果 {i + 1} / {len(text_parts)}  ]\n\n{part}")]
                )
                nodes = Nodes([node])
                try:
                    await event.send(event.chain_result([nodes]))
                except Exception as e:
                    yield event.plain_result(f"发送搜索结果失败: {str(e)}")
            del self.user_states[user_id]
            event.stop_event()

    async def _handle_waiting_engine(self, event: AstrMessageEvent, state: dict, user_id: str):
        """
        用户需要提供引擎名时的处理器

        参数:
            event: 消息事件
            state: 用户状态
            user_id: 用户ID

        返回:
            yield流程消息

        异常:
            输入错误会触发二次确认，超两次重试直接取消
        """
        example_engine = self.available_engines[0]
        message_text = get_message_text(event.message_obj).lower()
        if not message_text:
            yield event.plain_result(f"请回复有效的引擎名（如{example_engine}）")
            state["timestamp"] = time.time()
            event.stop_event()
            return
        if message_text in self.available_engines:
            state["engine"] = message_text
            if state.get("preloaded_img"):
                try:
                    async for result in self._perform_search(event, state["engine"], state["preloaded_img"]):
                        yield result
                except Exception as e:
                    yield event.plain_result(f"搜索失败: {str(e)}")
            else:
                state["step"] = "waiting_image"
                state["timestamp"] = time.time()
                yield event.plain_result(f"已选择引擎: {message_text}，请在30秒内发送一张图片，我会进行搜索")
        else:
            if message_text in ALL_ENGINES and message_text not in self.available_engines:
                yield event.plain_result(f"引擎 '{message_text}' 已被禁用，请联系管理员在配置中启用或选择其他引擎（如{example_engine}）")
                state["timestamp"] = time.time()
                async for result in self._send_engine_prompt(event, state):
                    yield result
            else:
                state.setdefault("invalid_attempts", 0)
                state["invalid_attempts"] += 1
                if state["invalid_attempts"] >= 2:
                    yield event.plain_result("连续两次输入错误的引擎名，已取消操作")
                    del self.user_states[user_id]
                else:
                    yield event.plain_result(f"引擎 '{message_text}' 不存在，请回复有效的引擎名（如{example_engine}）")
                    state["timestamp"] = time.time()
                    async for result in self._send_engine_prompt(event, state):
                        yield result
        event.stop_event()

    async def _handle_waiting_both(self, event, state, user_id):
        """
        等待用户同时给出引擎与图片输入的处理逻辑

        参数:
            event: 事件对象
            state: 用户状态
            user_id: 用户ID

        返回:
            yield文本提示/搜索结果

        异常:
            无
        """
        example_engine = self.available_engines[0]
        updated = False
        message_text = get_message_text(event.message_obj).lower()
        img_urls = get_img_urls(event.message_obj)
        if message_text and message_text in self.available_engines and not state.get('engine'):
            state["engine"] = message_text
            updated = True
        img_buffer = None
        if img_urls:
            img_buffer = await self._download_img(img_urls[0])
        elif is_image_url(message_text):
            img_buffer = await self._download_img(message_text)
        if img_buffer and not state.get('preloaded_img'):
            state["preloaded_img"] = img_buffer
            updated = True
        if state.get("engine") and state.get("preloaded_img"):
            try:
                async for result in self._perform_search(event, state["engine"], state["preloaded_img"]):
                    yield result
            except Exception as e:
                yield event.plain_result(f"搜索失败: {str(e)}")
            event.stop_event()
            return
        if updated:
            state["timestamp"] = time.time()
            async for result in self._send_engine_prompt(event, state):
                yield result
            event.stop_event()
        else:
            state["timestamp"] = time.time()
            is_invalid_engine_attempt = message_text and not is_image_url(message_text) and not state.get('engine')
            if is_invalid_engine_attempt:
                if message_text in ALL_ENGINES and message_text not in self.available_engines:
                    yield event.plain_result(
                        f"引擎 '{message_text}' 已被禁用，请联系管理员在配置中启用或选择其他引擎（如{example_engine}）"
                    )
                    async for result in self._send_engine_prompt(event, state):
                        yield result
                else:
                    state.setdefault("invalid_attempts", 0)
                    state["invalid_attempts"] += 1
                    if state["invalid_attempts"] >= 2:
                        yield event.plain_result("连续两次输入错误的引擎名，已取消操作")
                        del self.user_states[user_id]
                    else:
                        yield event.plain_result(
                            f"引擎 '{message_text}' 不存在，请回复有效的引擎名（如{example_engine}）"
                        )
                        async for result in self._send_engine_prompt(event, state):
                            yield result
            else:
                if not state.get('engine') and not state.get('preloaded_img'):
                    yield event.plain_result(f"请提供引擎名（如{example_engine}）和图片")
                elif not state.get('engine'):
                    yield event.plain_result(f"请提供引擎名（如{example_engine}）")
                elif not state.get('preloaded_img'):
                    yield event.plain_result("请提供图片")
            event.stop_event()

    async def _handle_waiting_image(self, event: AstrMessageEvent, state: dict, user_id: str):
        """
        处理仅等待图片输入的用户状态

        参数:
            event: 消息事件
            state: 用户状态
            user_id: 用户ID

        返回:
            yield消息

        异常:
            无
        """
        img_urls = get_img_urls(event.message_obj)
        message_text = get_message_text(event.message_obj)
        img_buffer = None
        if img_urls:
            img_buffer = await self._download_img(img_urls[0])
        elif is_image_url(message_text):
            img_buffer = await self._download_img(message_text)
        if img_buffer:
            async for result in self._perform_search(event, state["engine"], img_buffer):
                yield result
            event.stop_event()
        else:
            yield event.plain_result("请发送一张图片或图片链接")

    async def _handle_initial_search_command(self, event: AstrMessageEvent, user_id: str):
        """
        处理最初 "以图搜图" 命令自动分流与预处理

        参数:
            event: 消息事件
            user_id: 用户ID

        返回:
            yield提示或结果

        异常:
            无
        """
        if not self.available_engines:
            yield event.plain_result("当前没有可用的搜索引擎，请联系管理员在配置中启用至少一个引擎")
            event.stop_event()
            return
        example_engine = self.available_engines[0]
        message_text = get_message_text(event.message_obj)
        img_urls = get_img_urls(event.message_obj)
        parts = message_text.strip().split()
        if user_id in self.user_states:
            del self.user_states[user_id]
        engine = None
        url_from_text = None
        invalid_engine = False
        disabled_engine = False
        potential_engine = None
        if len(parts) > 1:
            if is_image_url(parts[1]):
                url_from_text = parts[1]
            else:
                potential_engine = parts[1].lower()
                if potential_engine in self.available_engines:
                    engine = potential_engine
                elif potential_engine in ALL_ENGINES:
                    disabled_engine = True
                else:
                    invalid_engine = True
                if len(parts) > 2 and is_image_url(parts[2]):
                    url_from_text = parts[2]
        preloaded_img = None
        if img_urls:
            preloaded_img = await self._download_img(img_urls[0])
        elif url_from_text:
            preloaded_img = await self._download_img(url_from_text)
        if disabled_engine:
            state = {
                "step": "waiting_both",
                "timestamp": time.time(),
                "preloaded_img": preloaded_img,
                "engine": None
            }
            self.user_states[user_id] = state
            yield event.plain_result(
                f"引擎 '{potential_engine}' 已被禁用，请联系管理员在配置中启用或选择其他引擎（如{example_engine}）")
            async for result in self._send_engine_prompt(event, state):
                yield result
            event.stop_event()
            return
        if invalid_engine:
            state = {
                "step": "waiting_both",
                "timestamp": time.time(),
                "preloaded_img": preloaded_img,
                "engine": None,
                "invalid_attempts": 1
            }
            self.user_states[user_id] = state
            yield event.plain_result(
                f"引擎 '{potential_engine}' 不存在，请提供有效的引擎名（如{example_engine}）")
            async for result in self._send_engine_prompt(event, state):
                yield result
            event.stop_event()
            return
        if engine and preloaded_img:
            try:
                async for result in self._perform_search(event, engine, preloaded_img):
                    yield result
            except Exception as e:
                yield event.plain_result(f"搜索失败: {str(e)}")
            event.stop_event()
            return
        state = {
            "step": "waiting_both",
            "timestamp": time.time(),
            "preloaded_img": preloaded_img,
            "engine": engine
        }
        self.user_states[user_id] = state
        async for result in self._send_engine_prompt(event, state):
            yield result
        event.stop_event()

    @filter.event_message_type(filter.EventMessageType.ALL)
    async def on_message(self, event: AstrMessageEvent):
        """
        插件消息收发主入口，处理各种状态下用户输入分发

        参数:
            event: AstrMessageEvent事件对象

        返回:
            yield响应内容

        异常:
            无
        """
        user_id = event.get_sender_id()
        message_text = get_message_text(event.message_obj)
        if message_text.strip().startswith("以图搜图"):
            async for result in self._handle_initial_search_command(event, user_id):
                yield result
            return
        state = self.user_states.get(user_id)
        if not state:
            return
        if time.time() - state["timestamp"] > 30:
            async for result in self._handle_timeout(event, user_id):
                yield result
            return
        handler = self.state_handlers.get(state.get("step"))
        if handler:
            async for result in handler(event, state, user_id):
                yield result
