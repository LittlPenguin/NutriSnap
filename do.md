# NutriSnap 阶段十一修复计划：流式 Model 建议、页面精简与设计同步

> **执行约束：** 本文件只记录修复计划。执行本计划时，应按任务顺序逐项实现、逐项验证、最后提交。当前阶段用户要求“本次不写代码，只写 do.md 计划”，因此本次只维护此计划文件。

## Goal

修复当前 Streamlit 应用中的饮食建议生成、页面结构、历史页文案、统计页展示、Open Design 本地设计稿和验收测试，使项目从“5 页面 + GPT 文案”调整为“4 页面 + Model 流式建议”。

## Architecture

保留现有技术架构：Streamlit 前端、SQLite 历史记录、ResNet18 食物识别、Food-101 子集、OpenAI 兼容接口饮食建议。内部模块名和数据库字段可继续保留 `gpt_*` 命名，避免引入破坏性迁移；用户可见 UI、设计稿和当前阶段文档统一使用 `Model`。

## Tech Stack

- Python
- Streamlit
- SQLite
- PyTorch ResNet18
- Food-101 子集
- OpenAI 兼容 Chat Completions / Responses API
- pytest
- ruff
- browser-use

---

## 0. 当前边界

### 本阶段要改

- 饮食建议改为流式生成。
- 用户可见 `GPT / gpt / GPT-5` 文案改为 `Model`。
- 删除 `about / 系统说明` 页面和导航入口。
- 访问 `?page=about` 时回退到 `recognition`。
- 历史记录页删除用户指定的降级提示文案。
- 统计页用“最新上传食物图”替代“近 7 日估算热量”。
- 统计页说明改为：`基于识别历史中的估算热量，不作为医学或营养诊断。`
- 本地 Open Design 归档同步为移动端 4 页 + PC 端 4 页。
- 更新测试、阶段文档和阻塞记录。
- 使用 `$browser-use` 验收，不使用 bundled `@浏览器`。

### 本阶段不改

- 不重建项目。
- 不更换 Streamlit。
- 不引入 Flask、React、shadcn 或原生 App。
- 不提交 `.env`、数据库、数据集、模型权重、测试图片或输出缓存。
- 不强制重命名内部文件、函数、环境变量或数据库表：
  - `services/gpt_advice_service.py`
  - `generate_gpt_advice`
  - `gpt_advice_log`
  - `OPENAI_MODEL`
  - 数据库字段 `gpt_advice`

---

## 1. 文件变更地图

### 代码文件

- 修改：`app.py`
  - 删除 `about_page` 路由。
  - 页面 key 从 5 个改为 4 个。
  - 非法 `page` 参数回退到 `recognition`。

- 修改：`services/gpt_advice_service.py`
  - 新增流式建议接口 `stream_model_advice()`。
  - 保留非流式 `generate_gpt_advice()` 兼容旧逻辑和测试。
  - 错误信息必须非敏感，不泄露 API Key。

- 修改：`ui/components.py`
  - 导航项从 5 个改为 4 个。
  - 移动端底部导航对应 4 项。
  - 用户可见 `GPT` 文案改为 `Model`。

- 修改：`ui/styles.py`
  - 移动端底部导航 CSS 从 5 列改为 4 列。
  - 保持固定底部导航不横向溢出。

- 修改：`ui/pages.py`
  - 食物识别页接入流式 Model 建议。
  - 上传图片 bytes 保存到 `st.session_state`，供统计页回显。
  - 历史页删除指定文案。
  - 统计页展示最新上传食物图和新说明文案。
  - 删除或停止使用 `about_page()`。

### 测试文件

- 修改：`tests/test_app_contract.py`
  - 页面合同从 5 页改为 4 页。
  - 删除 about 页面断言。
  - 增加 `?page=about` 回退断言。
  - 增加 Model 文案、历史页删除文案、统计页新展示断言。

- 修改：`tests/test_gpt_advice_service.py`
  - 增加流式 SSE 解析测试。
  - 增加缺 Key、HTTP 错误、空流错误测试。
  - 保留非流式 fallback 测试。

### 文档和设计文件

- 修改：`doc/10-阶段开发计划.md`
  - 追加阶段十一完成记录。

- 修改：`doc/开发阻塞记录.md`
  - 追加阶段十一验收记录。
  - 说明 about 页面已移除，不再作为当前 UI 验收对象。

- 修改：`opendesign-nutrisnap/index.html`
  - 本地设计归档改为移动端 4 页 + PC 端 4 页。
  - 删除系统说明页。
  - 删除系统说明导航入口。
  - 用户可见 `GPT` 改为 `Model`。

- 修改：`opendesign-nutrisnap/design.md`
  - 页面数量改为移动端 4 页 + PC 端 4 页。
  - 删除系统说明页描述。
  - 增加 Model 流式状态说明。

- 修改：`opendesign-nutrisnap/design-decision.md`
  - 同步页面结构和文案策略。

---

## 2. Task 1：先写失败测试

**Files:**

- Modify: `tests/test_app_contract.py`
- Modify: `tests/test_gpt_advice_service.py`

### Step 1.1：更新页面路由测试

在 `tests/test_app_contract.py` 中确认以下合同：

- `PAGE_KEYS` 只包含：
  - `recognition`
  - `history`
  - `calories`
  - `stats`
- `PAGE_KEYS` 不包含 `about`。
- `PAGE_LABELS` 只包含：
  - `食物识别`
  - `历史记录`
  - `热量表`
  - `统计分析`
- 源码不再导入或调用 `about_page`。

建议断言：

```python
def test_app_uses_four_page_routes():
    import app

    assert app.PAGE_KEYS == {"recognition", "history", "calories", "stats"}
    assert app.PAGE_LABELS == ["食物识别", "历史记录", "热量表", "统计分析"]
    assert "about" not in app.PAGE_KEYS
```

### Step 1.2：更新非法 about 回退测试

确认访问 `?page=about` 不会进入系统说明页，而是回退到识别页。

建议测试目标：

```python
def test_about_query_page_falls_back_to_recognition():
    import app

    assert app.resolve_page("about") == "recognition"
```

如果当前 `app.py` 没有 `resolve_page()`，执行阶段可新增一个小函数，避免路由逻辑散落在主流程里。

### Step 1.3：更新导航测试

断言：

- PC / 移动端导航包含：
  - `识别`
  - `历史`
  - `热量表`
  - `统计`
- 不包含：
  - `说明`
  - `系统说明`
- 不包含外链式跳转：
  - `href="?page=`

建议断言：

```python
def test_navigation_has_four_items_and_no_about_link(project_text):
    components_source = project_text("ui/components.py")

    assert "识别" in components_source
    assert "历史" in components_source
    assert "热量表" in components_source
    assert "统计" in components_source
    assert "系统说明" not in components_source
    assert "href=\"?page=" not in components_source
```

### Step 1.4：更新 Model 文案测试

断言用户可见 UI 包含：

- `Model 配置`
- `Model 饮食建议`
- `Model 生成中`
- `生成完毕`
- `失败：`

断言用户可见 UI 不再包含旧文案：

- `GPT 配置`
- `GPT 饮食建议`
- `GPT 生成中`
- `GPT 建议完成`

### Step 1.5：更新历史页文案删除测试

历史页不得包含：

```text
本地规则建议 当 GPT API key 未配置、网络失败或响应超时时，系统仍保存历史记录，并展示本地规则建议。
含 GPT 失败降级提示
GPT 失败降级
```

历史页可以保留：

```text
Model 建议摘要
```

### Step 1.6：更新统计页测试

统计页必须包含：

```text
最新上传食物图
说明
基于识别历史中的估算热量，不作为医学或营养诊断。
```

统计页不得包含：

```text
近 7 日估算热量
结果边界说明
```

### Step 1.7：新增流式建议服务测试

在 `tests/test_gpt_advice_service.py` 中新增测试：

- SSE `delta.content` 能正确拼接。
- `data: [DONE]` 正常结束。
- 缺少 API Key 返回 `error` 事件。
- HTTP 403 返回 `error` 事件，并包含非敏感错误原因。
- 空流返回 `error` 或 fallback，不伪装成功。

建议事件合同：

```python
{"type": "delta", "text": "部分文本"}
{"type": "done", "text": "完整建议"}
{"type": "error", "reason": "HTTP 403 PermissionDenied", "fallback": "本地规则建议..."}
```

### Step 1.8：运行失败测试

Run:

```powershell
pytest tests/test_app_contract.py tests/test_gpt_advice_service.py -q
```

Expected:

- 在实现前，关于 `stream_model_advice()`、四页面路由、Model 文案、统计页新文案的测试应失败。
- 失败原因应指向尚未实现的功能，而不是语法错误。

---

## 3. Task 2：实现流式 Model 建议服务

**Files:**

- Modify: `services/gpt_advice_service.py`

### Step 2.1：新增流式接口

新增函数：

```python
def stream_model_advice(
    food_name: str,
    weight_g: float,
    total_calorie: float,
    user_goal: str,
    settings: OpenAISettings | dict[str, Any] | None = None,
) -> Iterator[dict[str, str]]:
    ...
```

### Step 2.2：请求优先使用 Chat Completions

请求 endpoint：

```text
chat/completions
```

payload：

```python
{
    "model": settings.model,
    "messages": [
        {"role": "system", "content": "你是饮食记录建议助手，只提供饮食记录参考，不做医学或营养诊断。"},
        {"role": "user", "content": prompt},
    ],
    "max_tokens": 180,
    "stream": True,
}
```

### Step 2.3：解析 SSE

解析规则：

- 跳过空行。
- 只处理 `data:` 开头的行。
- `data: [DONE]` 表示结束。
- JSON 中优先读取：
  - `choices[0].delta.content`
  - `choices[0].text`
  - `delta`
  - `output_text_delta`

### Step 2.4：失败时返回错误事件

失败事件必须包含：

```python
{
    "type": "error",
    "reason": "非敏感错误原因",
    "fallback": "本地规则建议文本",
}
```

要求：

- 不输出 API Key。
- 不打印完整敏感 URL。
- HTTP 错误需要保留状态码和简短原因，例如 `HTTP 403 PermissionDenied`。
- 网络超时显示 `timeout`。
- 空流显示 `empty streaming response`。

### Step 2.5：保留非流式兼容函数

`generate_gpt_advice()` 保留，继续用于旧测试或非流式兜底。其用户可见错误前缀改为 `Model 调用失败`，不要新增 `GPT` 文案。

### Step 2.6：运行服务测试

Run:

```powershell
pytest tests/test_gpt_advice_service.py -q
```

Expected:

- 流式解析测试通过。
- 缺 Key fallback 测试通过。
- HTTP 错误原因测试通过。

---

## 4. Task 3：删除 about 页面并改为 4 页面导航

**Files:**

- Modify: `app.py`
- Modify: `ui/components.py`
- Modify: `ui/styles.py`
- Modify: `ui/pages.py`

### Step 3.1：修改 app 路由

`app.py` 页面配置改为：

```python
PAGE_LABELS = ["食物识别", "历史记录", "热量表", "统计分析"]
PAGE_KEYS = {"recognition", "history", "calories", "stats"}
DEFAULT_PAGE = "recognition"
```

建议增加：

```python
def resolve_page(raw_page: str | None) -> str:
    if raw_page in PAGE_KEYS:
        return raw_page
    return DEFAULT_PAGE
```

删除：

```python
from ui.pages import about_page
```

删除：

```python
elif active_page == "about":
    about_page()
```

### Step 3.2：修改导航项

`ui/components.py` 中 `PAGE_ITEMS` 改为 4 项：

```python
PAGE_ITEMS = [
    ("食物识别", "recognition", "识别"),
    ("历史记录", "history", "历史"),
    ("热量表", "calories", "热量表"),
    ("统计分析", "stats", "统计"),
]
```

### Step 3.3：修改移动端底部导航

移动端底部导航使用 4 列：

```python
columns = st.columns(4)
```

CSS：

```css
.mobile-bottom-nav {
  grid-template-columns: repeat(4, minmax(0, 1fr));
}
```

要求：

- 不使用 `href="?page=..."`
- 点击后使用 `st.query_params["page"] = key` 和 `st.rerun()`
- 当前页高亮
- 390×844 下不横向溢出

### Step 3.4：删除 about 页面实现

`ui/pages.py` 中删除或停止使用：

```python
def about_page(...):
    ...
```

如果为了兼容测试暂不删除函数，也不得从路由调用，并且导航不应暴露入口。推荐直接删除，减少误用。

### Step 3.5：运行页面合同测试

Run:

```powershell
pytest tests/test_app_contract.py -q
```

Expected:

- 四页面路由测试通过。
- `about` 回退测试通过。
- 导航无 `系统说明`。
- 源码无 `href="?page=`。

---

## 5. Task 4：食物识别页接入流式 Model 建议

**Files:**

- Modify: `ui/pages.py`

### Step 4.1：上传图片写入 session

在用户上传图片后保存 bytes：

```python
st.session_state["latest_uploaded_image_bytes"] = uploaded_file.getvalue()
st.session_state["latest_uploaded_image_name"] = uploaded_file.name
```

注意：

- 只保存在当前会话。
- 不写入 SQLite。
- 不写入磁盘。
- 不提交测试图片。

### Step 4.2：替换非流式建议调用

点击“计算热量并生成建议”后：

1. 显示状态：`Model 生成中`
2. 调用 `stream_model_advice(...)`
3. 使用 `st.empty()` 逐步回显增量文本
4. 成功后显示：`生成完毕`
5. 失败后显示：`失败：<错误原因>`

### Step 4.3：成功展示

成功卡片标题：

```text
Model 饮食建议
```

成功状态：

```text
生成完毕
```

### Step 4.4：失败展示

失败状态：

```text
失败：HTTP 403 PermissionDenied
```

失败降级卡片标题：

```text
失败降级建议
```

要求：

- 本地规则建议不得伪装为 Model 成功。
- 错误原因不得包含 API Key。
- 保存历史时保存最终展示给用户的建议文本。
- 日志状态记录 `success`、`error` 或 `fallback`。

### Step 4.5：用户可见文案替换

替换：

- `GPT 配置` -> `Model 配置`
- `GPT 饮食建议` -> `Model 饮食建议`
- `GPT 生成中` -> `Model 生成中`
- `GPT 建议完成` -> `生成完毕`
- `GPT API Key` -> `Model API Key`

### Step 4.6：运行识别页相关测试

Run:

```powershell
pytest tests/test_app_contract.py tests/test_gpt_advice_service.py -q
```

Expected:

- Model 文案测试通过。
- 流式服务测试通过。

---

## 6. Task 5：历史页和统计页调整

**Files:**

- Modify: `ui/pages.py`

### Step 5.1：删除历史页指定文案

删除用户可见文案：

```text
本地规则建议 当 GPT API key 未配置、网络失败或响应超时时，系统仍保存历史记录，并展示本地规则建议。
含 GPT 失败降级提示
```

同时删除或改名：

- `GPT 失败降级`
- `GPT 建议摘要`
- `GPT 失败时使用本地规则建议`

改为：

```text
Model 建议摘要
```

### Step 5.2：统计页替换趋势图标题和内容

删除：

```text
近 7 日估算热量
```

改为：

```text
最新上传食物图
```

展示逻辑：

```python
image_bytes = st.session_state.get("latest_uploaded_image_bytes")
if image_bytes:
    st.image(
        image_bytes,
        caption=st.session_state.get("latest_uploaded_image_name", "最新上传食物图"),
        use_container_width=True,
    )
else:
    st.info("暂无上传图片")
```

### Step 5.3：统计页说明文案

删除：

```text
结果边界说明
统计分析基于识别历史中的估算热量，不代表真实摄入精确值，也不作为医学或营养诊断。
```

改为：

```text
说明
基于识别历史中的估算热量，不作为医学或营养诊断。
```

### Step 5.4：运行页面测试

Run:

```powershell
pytest tests/test_app_contract.py -q
```

Expected:

- 历史页旧文案不存在。
- 统计页新文案存在。
- 统计页旧文案不存在。

---

## 7. Task 6：同步本地 Open Design 设计稿

**Files:**

- Modify: `opendesign-nutrisnap/index.html`
- Modify: `opendesign-nutrisnap/design.md`
- Modify: `opendesign-nutrisnap/design-decision.md`

### Step 6.1：同步 index.html

设计稿结构改为：

- 移动端 4 页：
  - 食物识别
  - 历史记录
  - 热量表
  - 统计分析
- PC 端 4 页：
  - 食物识别工作台
  - 历史记录
  - 食物热量表
  - 统计分析

删除：

- 移动端系统说明页
- PC 端系统说明页
- `about`
- `系统说明`
- `说明` 导航入口

替换：

- `GPT` -> `Model`
- `近 7 日估算热量` -> `最新上传食物图`
- `结果边界说明` -> `说明`

增加状态：

- `Model 生成中`
- `生成完毕`
- `失败：错误原因`

### Step 6.2：同步 design.md

页面数量写为：

```text
移动端 4 个独立页面 + PC 端 4 个宽屏页面
```

删除系统说明页描述。

说明：

```text
饮食建议使用 Model 流式生成，状态包括 Model 生成中、生成完毕、失败：错误原因。
```

### Step 6.3：同步 design-decision.md

记录设计决策：

- 当前不再展示系统说明页。
- 当前 UI 以 4 个核心业务页面为准。
- 饮食建议统一称为 Model 建议。
- 失败时显示错误原因并展示降级建议，不伪装为成功。

### Step 6.4：本地设计稿文本检查

Run:

```powershell
rg -n "GPT|GPT-5|系统说明|about|近 7 日估算热量|结果边界说明|含 GPT 失败降级提示" opendesign-nutrisnap
```

Expected:

- 不再出现用户可见旧文案。
- 如果历史说明中必须保留旧阶段名称，需要明确标注为历史记录；推荐本地设计稿中完全移除。

---

## 8. Task 7：同步阶段文档和阻塞记录

**Files:**

- Modify: `doc/10-阶段开发计划.md`
- Modify: `doc/开发阻塞记录.md`

### Step 7.1：更新阶段开发计划

在 `doc/10-阶段开发计划.md` 追加：

```markdown
## 12. 阶段十一：流式 Model 建议、页面精简与设计同步

### 开发目标

将饮食建议改为流式 Model 生成，删除系统说明页，修复历史页和统计页文案，并同步 Open Design 本地设计稿。

### 已完成

是。已完成流式 Model 建议、4 页面导航、about 回退、历史页文案删除、统计页最新上传图片回显、Open Design 本地设计稿同步和测试合同更新。

### 完成提交

阶段十一：修复流式 Model 建议与页面结构，较上次删除系统说明页并同步设计稿

### 验证证据

- `pytest -q`
- `ruff check .`
- `python -m py_compile app.py services/*.py train/*.py ui/*.py tests/*.py`
- `$browser-use` 打开 `http://127.0.0.1:8501` 验收 PC 和 390×844 模拟移动端。

### 阻塞记录

无新增用户侧阻塞项。真实 Model 调用继续使用 `.env` 或页面会话配置，不记录真实 Key。
```

### Step 7.2：更新阻塞记录

在 `doc/开发阻塞记录.md` 追加：

```markdown
## 阶段十一验收记录

- B-001：已解决。Model 真实建议能力使用 `.env` 或页面会话配置；文档和日志不记录真实 API Key。
- B-003：已解决或按当前真实状态记录。本地权重如已生成并通过 testData 推理验收，应记录为“本地已验收，权重不提交”；如未生成，应保留为未完成。
- B-004：不做真机校验。当前移动端验收口径为浏览器模拟 390×844。
- about / 系统说明页面已删除，不再作为当前 UI 验收对象。
```

要求：

- 不写真实 API Key。
- 不写敏感 Base URL。
- 不新增 `GPT` 用户可见文案；当前阶段统一写 `Model`。

---

## 9. Task 8：自动化验证

**Files:**

- No direct file changes unless tests fail.

### Step 8.1：运行全量测试

Run:

```powershell
pytest -q
```

Expected:

- 全部测试通过。

### Step 8.2：运行 ruff

Run:

```powershell
ruff check .
```

Expected:

- 无 lint 错误。
- 如出现未使用 import，删除未使用项，不做无关重构。

### Step 8.3：运行 py_compile

PowerShell 推荐命令：

```powershell
$files = @("app.py") + (Get-ChildItem services,train,ui,tests -Filter *.py -Recurse | ForEach-Object { $_.FullName })
python -m py_compile $files
```

Expected:

- 无输出或无错误退出。

### Step 8.4：文本检查

Run:

```powershell
rg -n "href=\"\\?page=|系统说明|about|近 7 日估算热量|结果边界说明|含 GPT 失败降级提示" app.py ui tests opendesign-nutrisnap
```

Expected:

- `app.py`、`ui/`、`opendesign-nutrisnap/` 中不出现旧用户可见文案。
- `tests/` 中如果出现旧文案，只能作为负向断言存在。

Run:

```powershell
rg -n "GPT|gpt|GPT-5" app.py ui opendesign-nutrisnap
```

Expected:

- 用户可见 UI 和设计稿中不出现 `GPT`。
- 内部技术字段如 `gpt_advice` 若位于 UI 展示之外，可保留。

---

## 10. Task 9：browser-use 验收

**Files:**

- No direct file changes unless验收发现问题。

### Step 9.1：启动 Streamlit

Run:

```powershell
streamlit run app.py --server.address=127.0.0.1 --server.port=8501 --server.headless=true
```

要求：

- 验收后停止服务。
- 不让服务长期留在后台。

### Step 9.2：PC 页面验收

使用 `$browser-use`：

打开：

```text
http://127.0.0.1:8501
```

检查：

- 顶部不被 Streamlit header 遮挡。
- 导航只有 4 项：
  - 食物识别
  - 历史记录
  - 热量表
  - 统计分析
- 不显示系统说明入口。
- 页面用户可见文案使用 `Model`。

### Step 9.3：about 回退验收

打开：

```text
http://127.0.0.1:8501/?page=about
```

检查：

- 回退到食物识别页。
- 不显示系统说明页。
- 不显示系统说明导航入口。

### Step 9.4：真实图片链路验收

上传：

```text
D:\白云\下\ai\end\testData\900fa129383aecfbebd0f257ee1ca668.jpg
```

检查：

- 图片预览显示。
- 识别结果显示。
- Top-3 显示。
- 估算热量显示。
- Model 配置入口可见。
- 生成建议时先显示 `Model 生成中`。
- 成功后显示 `生成完毕`。
- 失败时显示 `失败：<错误原因>`，并显示降级建议。

说明：

- 如果流式返回很快，可能难以人工捕捉 `Model 生成中`，但最终状态必须是 `生成完毕` 或 `失败：<错误原因>`。
- 如果 API 失败，验收错误原因显示和降级建议，不视为页面功能失败。

### Step 9.5：移动端模拟验收

使用 `$browser-use` 或浏览器调试能力设置视口：

```text
390 × 844
```

检查：

- 底部导航为 4 项。
- 4 项不换行。
- 无横向滚动。
- 点击 `识别 / 历史 / 热量表 / 统计` 均为站内切换。
- 统计页显示 `最新上传食物图`。
- 统计页显示：

```text
说明
基于识别历史中的估算热量，不作为医学或营养诊断。
```

### Step 9.6：停止 Streamlit

验收完成后停止本地服务，并在最终说明中写明：

```text
Streamlit 验收服务已停止。
```

---

## 11. Task 10：提交与推送

**Files:**

- Stage only relevant tracked files and `do.md`。

### Step 10.1：检查 Git 状态

Run:

```powershell
git status --short
```

确认不提交：

- `.env`
- `dataset/`
- `models/*.pth`
- `data/*.db`
- `testData/`
- `outputs/`
- `.venv/`

### Step 10.2：暂存文件

Run:

```powershell
git add app.py services/gpt_advice_service.py ui/components.py ui/pages.py ui/styles.py tests/test_app_contract.py tests/test_gpt_advice_service.py doc/10-阶段开发计划.md doc/开发阻塞记录.md do.md
```

说明：

- `opendesign-nutrisnap/` 当前按项目规则为本地设计归档，通常被 `.gitignore` 忽略，不强制提交。
- 如果用户后续明确要求提交设计归档，再单独调整 `.gitignore` 或使用 `git add -f`，本阶段默认不强制。

### Step 10.3：提交

Run:

```powershell
git commit -m "阶段十一：修复流式 Model 建议与页面结构，较上次删除系统说明页并同步设计稿"
```

### Step 10.4：推送

Run:

```powershell
git push origin main
```

如果 SSH 推送失败：

- 记录失败原文。
- 不改远程地址。
- 不切换 HTTPS。
- 不泄露密钥。

---

## 12. Acceptance Checklist

- [ ] `do.md` 已存在且中文无乱码。
- [ ] 自动化测试通过：`pytest -q`。
- [ ] 静态检查通过：`ruff check .`。
- [ ] 编译检查通过：`python -m py_compile ...`。
- [ ] 应用只有 4 个有效页面。
- [ ] 导航不包含系统说明。
- [ ] `?page=about` 回退到食物识别。
- [ ] 食物识别页使用 `Model 配置`、`Model 饮食建议`、`Model 生成中`、`生成完毕`、`失败：`。
- [ ] 历史页删除用户指定的两处降级提示文案。
- [ ] 统计页显示 `最新上传食物图`。
- [ ] 统计页显示新说明：`基于识别历史中的估算热量，不作为医学或营养诊断。`
- [ ] 本地 Open Design 归档为移动端 4 页 + PC 端 4 页。
- [ ] browser-use PC 验收通过。
- [ ] browser-use 390×844 移动端模拟验收通过。
- [ ] `.env`、数据集、模型权重、数据库、测试图片未提交。
- [ ] 中文提交信息已提交。
- [ ] 推送到 `origin/main` 成功，或已记录 SSH 失败原因。

---

## 13. Risks And Notes

- 流式接口兼容性取决于用户 `.env` 中的 `OPENAI_BASE_URL` 所对应网关是否支持 SSE。若不支持，应显示 `失败：<错误原因>` 并展示降级建议。
- testData 图片可能不属于当前 12 类 Food-101 子集之一，真实图片验收只验证业务链路可用，不保证语义预测完全正确。
- 统计页“最新上传食物图”只保存在当前 Streamlit 会话，刷新或重启后消失；这是当前计划要求，不写数据库。
- 删除系统说明页后，课程汇报中的技术说明仍可保留在文档或报告中，但不作为当前 App 页面展示。
- 历史阶段文档中可能仍有旧 `GPT` 记录；当前阶段新增文档和用户可见 UI 应统一使用 `Model`。
