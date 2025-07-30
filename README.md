# 适配 AstrBot 的图片反搜插件

> ⚡ **核心代码基于**：[kitUIN/PicImageSearch](https://github.com/kitUIN/PicImageSearch)

## 🛠 安装方法

### 方式一：插件市场

- 打开 **AstrBot WebUI** → **插件市场** → 右上角 **Search**
- 搜索与本项目相关的关键词，找到插件后点击安装
- 推荐直接用唯一标识符搜索：  
  ```
  astrbot_plugin_img_rev_searcher
  ```

### 方式二：Github 仓库链接

- 打开 **AstrBot WebUI** → **插件管理** → **+ 安装**
- 在出现的输入框内粘贴以下仓库地址并点击安装：
  ```
  https://github.com/drdon1234/astrbot_plugin_img_rev_searcher
  ```

### 📦 依赖库安装（重要）

请先安装以下依赖库：

- httpx>=0.23.0
- Pillow>=9.0.0
- selenium>=4.0.0
- pyquery
- typing_extensions

在终端执行：

```
pip install -r requirements.txt
```
或逐个安装：

```
pip install <module>
```
*使用具体模块名替换 &lt;module&gt;*

## 🚀 使用说明

| 指令类型 | 格式                | 说明                    |
|:----:|:------------------|:-----------------------|
| 指令头  | `以图搜图`            | 启动图片反搜流程        |
|  参数  | `引擎名`，`图片文件/图片链接` | 两个参数都必填，顺序不限 |

### 指令帮助

#### 方式一：根据提示分步发送
1. 发送 `以图搜图`
2. 发送 `<引擎名>` 和 / 或 `<图片文件/图片链接>`
3. 若有缺漏，补充缺少的参数

#### 方式二：先发送部分参数再补齐
- 发送 `以图搜图 <图片文件/图片链接>`，再发送 `<引擎名>`
- 发送 `以图搜图 <引擎名>`，再发送 `<图片文件/图片链接>`

#### 方式三：一次性发送全部参数
- 发送 `以图搜图 <引擎名> <图片文件/图片链接>`
- 发送 `以图搜图 <图片文件/图片链接> <引擎名>`

#### 方式四：引用历史消息再补齐
- 引用一张图片并发送 `以图搜图 <引擎名>`

### 📝 注意事项
- 图片参数支持 `.gif` 格式，将会截取 **第一帧** 进行搜索

### 支持的搜索引擎

| 引擎        | 网址                                                        | 二次元专用 | 中国大陆直连 |
|:------------|:------------------------------------------------------------|:----------:|:-------------:|
| animetrace  | [animetrace.com](https://www.animetrace.com/)               | ✅         | ✅            |
| baidu       | [graph.baidu.com](https://graph.baidu.com/)                  | ❌         | ✅            |
| bing        | [bing.com/images/search](https://www.bing.com/images/search)| ❌         | ❌            |
| copyseeker  | [copyseeker.net](https://copyseeker.net/)                   | ❌         | ❌            |
| ehentai     | [e-hentai.org](https://e-hentai.org/)                        | ✅         | ❌            |
| google      | [lens.google.com](https://lens.google.com/)                  | ❌         | ❌            |
| saucenao    | [saucenao.com](https://saucenao.com/)                        | ✅         | ✅            |
| tineye      | [tineye.com/search/](https://tineye.com/search/)             | ❌         | ❌            |

## ⚠️ 配置文件说明

### **在使用前请核对并根据需要修改配置文件**：

### 1. 打开 AstrBot WebUI → `插件管理` → 找到本插件 → `操作` → `插件配置`
### 2. 根据需要进行设置

> ### 支持自动获取 Google Lens Cookie 并管理更新（推荐）
> 在插件配置中启用 `Google Lens Cookie 自动获取设置` -> `是否启用自动获取 Cookie`
> 
> #### 注意事项
> 
> 1. 桌面端
> - 确认已安装 **chrome 浏览器**
> 
> 2. docker
> - 确认已安装 **selenium 官方镜像** `selenium/standalone-chrome`
> - 配置 `remote_addr` 默认值 `http://localhost:4444/wd/hub`
> - 如果 `remote_addr` 为公网地址，请将 `localhost` 改为具体地址或域名

> ### 支持预设 Google Lens Cookie （不推荐）  
> 请按以下步骤获取无痕模式下有效的 Google Cookie：
> 
> 1. 打开浏览器无痕窗口  
> 2. 按 `F12` 打开开发者工具，切换到"网络(Network)"标签，过滤"Fetch/XHR"  
> 3. 访问 [https://image.google.com/](https://image.google.com/)  并上传任意图片进行搜索
> 4. 找到以 `search?vsrid=` 开头的请求，查看请求头中的 `Cookie` 字段  
> 5. 复制完整的 Cookie 内容，替换到 `config.json` 中 `default_cookies` 的 `google_lens` 项
> 
> **注意：**  
> - 有效cookie的充要参数为`NID= `
> - 无痕模式cookie有效期限约1天
> - 登录状态cookie有效期极短，不建议使用

## 📝 注意事项
- `exhentai` 对 **地区** 有严格检查，要求 **优质欧美 IP**

<br><br>

---

# API 参数文档

## AnimeTrace

**支持的搜索方式：**
1. 🔗 通过图片URL搜索
2. 📁 通过上传本地图片文件搜索  
3. 📄 通过提供base64编码图片搜索

### 参数

| 参数 | 类型 | 说明 |
|------|------|------|
| `url` | `Optional[str]` | 要搜索的图片URL |
| `file` | `Union[str, bytes, Path, None]` | 本地图片文件，可以是路径字符串、字节数据或Path对象 |
| `base64` | `Optional[str]` | Base64编码的图片数据 |
| `model` | `Optional[str]` | 识别模型（默认：full_game_model_kira）|
| `is_multi` | `Optional[int]` | 多角色搜索模式（默认：None）|
| `ai_detect` | `Optional[int]` | AI检测模式（默认：None）|

#### 可用模型
- `anime_model_lovelive`
- `pre_stable` 
- `anime`
- `full_game_model_kira`

### 返回值

```
AnimeTraceResponse
```
包含：
- ✨ 检测到的角色及其来源作品
- 📍 边界框坐标
- 🏷️ 其他元数据（trace_id、AI检测标识）

### 异常

- `ValueError`: 如果未提供`url`、`file`或`base64`中的任何一个

> **⚠️ 注意事项**
> - 只能提供`url`、`file`或`base64`中的一个
> - URL和base64搜索使用JSON POST请求
> - 文件上传使用multipart/form-data POST请求

## Baidu

**支持的搜索方式：**
1. 🔗 通过图片URL搜索
2. 📁 通过上传本地图片文件搜索

### 参数

| 参数 | 类型 | 说明 |
|------|------|------|
| `url` | `Optional[str]` | 要搜索的图片URL |
| `file` | `Union[str, bytes, Path, None]` | 本地图片文件 |

### 返回值

```
BaiDuResponse
```
包含搜索结果和元数据。如果未找到匹配项或存在'noresult'卡片，则返回空结果。

### 异常

- `ValueError`: 如果既未提供`url`也未提供`file`

> **⚠️ 注意事项**
> - 只能提供`url`或`file`中的一个
> - 搜索过程涉及对百度API的多次HTTP请求
> - 响应格式因是否找到匹配项而异

## Bing

**支持的搜索方式：**
1. 🔗 通过图片URL搜索
2. 📁 通过上传本地图片文件搜索

### 参数

| 参数 | 类型 | 说明 |
|------|------|------|
| `url` | `Optional[str]` | 要搜索的图片URL |
| `file` | `Union[str, bytes, Path, None]` | 本地图片文件 |

### 返回值

```
BingResponse
```
包含搜索结果和元数据的对象。

### 异常

- `ValueError`: 如果既未提供`url`也未提供`file`
- `ValueError`: 如果上传图片时无法找到BCID

## Copyseeker

**支持的搜索方式：**
1. 🔗 通过图片URL搜索
2. 📁 通过上传本地图片文件搜索

### 参数

| 参数 | 类型 | 说明 |
|------|------|------|
| `url` | `Optional[str]` | 要搜索的图片URL |
| `file` | `Union[str, bytes, Path, None]` | 本地图片文件 |

### 返回值

```
CopyseekerResponse
```
如果无法获得发现ID，则返回空响应。

## EHentai/ExHentai

**支持的搜索方式：**
1. 🔗 通过图片URL搜索
2. 📁 通过上传本地图片文件搜索

### 参数

| 参数 | 类型 | 说明 |
|------|------|------|
| `url` | `Optional[str]` | 要搜索的图片URL |
| `file` | `Union[str, bytes, Path, None]` | 本地图片文件 |
| `is_ex` | `bool` | 是否使用ExHentai而不是E-Hentai（默认：False）|
| `covers` | `bool` | 是否包含封面搜索结果（默认：False）|
| `similar` | `bool` | 是否包含相似结果（默认：True）|
| `exp` | `bool` | 是否启用实验性搜索模式（默认：False）|

### 返回值

```
EHentaiResponse
```
包含：
- 📚 相似图库条目
- 🔗 图库URL和标题
- 📊 相似度评分
- 🏷️ 搜索结果中的其他元数据

### 异常

- `ValueError`: 如果既未提供`url`也未提供`file`
- `RuntimeError`: 如果在ExHentai上搜索时没有适当的身份验证

> **🔐 重要提示**
> - 对于ExHentai搜索，必须在request_kwargs中提供有效的cookies
> - 搜索行为受初始化时设置的covers、similar和exp标志影响

## GoogleLens

**支持的搜索方式：**
1. 🔗 通过图片URL搜索
2. 📁 通过上传本地图片文件搜索

### 参数

| 参数 | 类型 | 说明                                        |
|------|------|-------------------------------------------|
| `url` | `Optional[str]` | 要搜索的图片URL                                 |
| `file` | `Union[str, bytes, Path, None]` | 本地图片文件                                    |
| `base_url` | `str` | Google Lens搜索的基础URL                       |
| `search_url` | `str` | Google搜索结果的基础URL                          |
| `search_type` | `Literal` | 搜索类型（默认：exact_matches）                    |
| `q` | `Optional[str]` | 搜索查询参数（仅在search_type不为'exact_matches'时适用） |
| `hl` | `str` | 语言参数（默认：en）                               |
| `country` | `str` | 区域设置参数（默认：HK）                             |
| `max_results` | `int` | 最大搜索结果数（默认：50）                            |

#### 搜索类型选项
- `all` - 全部搜索
- `products` - 产品搜索
- `visual_matches` - 视觉匹配
- `exact_matches` - 精确匹配

### 异常

- `ValueError`: 如果search_type为'exact_matches'且提供了q参数
- `ValueError`: 如果search_type不是有效选项之一

## SauceNAO

**支持的搜索方式：**
1. 🔗 通过图片URL搜索
2. 📁 通过上传本地图片文件搜索

### 参数

| 参数 | 类型 | 说明 |
|------|------|------|
| `url` | `Optional[str]` | 要搜索的图片URL |
| `file` | `Union[str, bytes, Path, None]` | 本地图片文件 |
| `api_key` | `str` | SauceNAO API密钥（必需） |
| `hide` | `int` | 隐藏级别（默认：3） |
| `numres` | `int` | 返回结果数量（默认：5） |
| `minsim` | `int` | 最低相似度（默认：30） |
| `output_type` | `int` | 输出类型（默认：2，表示JSON输出） |
| `testmode` | `int` | 测试模式（默认：0） |
| `dbmask` | `Optional[int]` | 数据库掩码（包含） |
| `dbmaski` | `Optional[int]` | 数据库掩码（排除） |
| `db` | `int` | 搜索的数据库ID（默认：999，表示所有） |
| `dbs` | `Optional[list[int]]` | 特定的数据库ID列表 |

### 返回值

```
SauceNAOResponse
```
包含：
- 🎯 带有相似度评分的搜索结果
- 🖼️ 来源信息和缩略图
- 📈 其他元数据（状态码、搜索配额）

### API限制

#### 免费账户限制
| 限制类型 | 数量 |
|----------|------|
| 每日搜索次数 | 150次 |
| 每30秒搜索次数 | 4次 |

> **📊 结果排序**
> 结果按相似度评分降序排列

## Tineye

使用图片URL或本地图片文件搜索网络上的匹配图片。初始搜索后，检索匹配图片的域名信息。

### 参数

| 参数 | 类型 | 说明 |
|------|------|------|
| `url` | `Optional[str]` | 要搜索的图片URL |
| `file` | `Union[str, bytes, Path, None]` | 本地图片文件路径 |
| `show_unavailable_domains` | `bool` | 是否包含来自不可用域名的结果（默认：False） |
| `domain` | `str` | 过滤特定域名的结果（默认：""） |
| `sort` | `str` | 排序标准（默认：score） |
| `order` | `str` | 排序顺序（默认：desc） |
| `tags` | `str` | 逗号分隔的过滤标签（默认：""） |

### 排序选项

#### sort参数
| 值 | 说明 |
|----|------|
| `score` | 按匹配评分排序 |
| `crawl_date` | 按爬取日期排序 |
| `size` | 按图片大小排序 |

#### order参数 + 效果组合
| sort + order | 效果 |
|--------------|------|
| `score` + `desc` | 最佳匹配优先 |
| `score` + `asc` | 最多变化优先 |
| `crawl_date` + `desc` | 最新图片优先 |
| `crawl_date` + `asc` | 最旧图片优先 |
| `size` + `desc` | 最大图片优先 |

### 返回值

```
TineyeResponse
```
包含搜索结果、域名信息和元数据。

---

# 搜索流程及结果示例
<div align="left">

### 第一步：触发搜索流程
<img src="https://github.com/user-attachments/assets/e06a19ab-cd83-4621-95fe-65916a13b37b" alt="1" width="40%"><br><br>

### 第二步：收到图片格式的搜索结果
<img src="https://github.com/user-attachments/assets/56404911-d129-4ebe-ae25-6bddc1e4b26d" alt="2" width="40%"><br><br>

### 第三步：选择是否需要文字格式的搜索结果
<img src="https://github.com/user-attachments/assets/2677d9d0-7908-4b6c-ba3c-cede100b4192" alt="3" width="40%"><br><br>

### 第四步：收到文字格式的搜索结果
<img src="https://github.com/user-attachments/assets/92e3012a-b9c7-4f5b-8e52-80b5791acb66" alt="4" width="40%">

</div>
