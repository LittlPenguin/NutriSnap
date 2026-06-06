# NutriSnap 阶段十二修复计划：消除 Model 建议生成后的重复渲染

> **执行约束：** 本文件记录阶段十二修复计划。执行时按任务顺序实现、验证、更新阶段文档并提交。`.env`、数据库、数据集、模型权重、测试图片和缓存文件不得提交。

## Goal

修复食物识别页在 Model 建议生成完成后重复显示状态条、流程状态、热量卡片和建议卡片的问题，让页面只保留一组最终结果。

## Architecture

重复内容来自 `ui/pages.py` 中两个渲染入口同时输出最终结果：`render_model_advice_stream()` 在流式生成结束时直接渲染最终建议，`recognition_page()` 又从 `st.session_state.advice_result` 渲染持久结果。修复方向是把最终展示收敛为单一入口：流式函数只显示临时生成过程，生成结束后返回结构化结果；页面保存结果后 `st.rerun()`，最终热量和建议只由统一结果渲染函数输出一次。

## Tech Stack

- Python
- Streamlit
- SQLite
- OpenAI 兼容 Model 接口
- pytest
- ruff
- browser-use

---

## 1. 当前问题

用户在点击“计算热量并生成建议”后，页面会出现重复内容，例如：

```text
生成完毕
Model 建议已完成。
Model 饮食建议
...
未上传
上传框默认状态
已上传预览
图片预览
识别完成
类别、置信度、Top-3
Model 生成中
...
估算热量
321 kcal
...
Model 饮食建议
...
```

根因：

- `render_model_advice_stream()` 内部渲染了流式过程、完成状态和最终建议卡片。
- `recognition_page()` 在同一轮运行末尾又读取 `st.session_state.calorie_result` 和 `st.session_state.advice_result`，再次渲染热量卡、状态条和建议卡。
- `workflow_state_strip()` 本身会展示整组状态，如果被多处调用，会让用户误以为流程状态重复堆叠。

---

## 2. 修复范围

### 本阶段要改

- `render_model_advice_stream()` 只保留临时生成过程，不渲染最终 `Model 饮食建议` 卡片。
- 新增统一最终结果渲染函数，只从一个入口显示估算热量和建议结果。
- 点击生成建议后，保存历史和日志，再写入 session state 并调用 `st.rerun()`。
- 补充测试，防止流式函数再次渲染最终卡片或调用 `workflow_state_strip()`。
- 更新 `doc/10-阶段开发计划.md` 和 `doc/开发阻塞记录.md`。
- 使用 `$browser-use` 验收真实页面，不使用 bundled `@浏览器`。

### 本阶段不改

- 不新增页面，不恢复系统说明页。
- 不修改数据库 schema。
- 不改变 Model 配置逻辑。
- 不改变 ResNet18 识别、热量估算、历史保存和统计页逻辑。
- 不提交 `.env`、数据库、数据集、模型权重、测试图片或缓存。

---

## 3. 实施步骤

### Task 1：拆分流式过程与最终展示

**Files**

- Modify: `ui/pages.py`

**步骤**

1. 从 `render_model_advice_stream()` 中删除 `workflow_state_strip(...)` 调用。
2. 将流式增量卡片标题改为 `Model 生成中`，避免生成过程被当成最终建议。
3. 成功完成时只返回：

```python
{"status": "success", "advice": final_text}
```

4. 失败时只返回：

```python
{"status": "error", "advice": fallback, "error_reason": reason}
```

5. 成功或失败后清理 `advice_placeholder`，避免临时内容和最终内容同时停留。

### Task 2：新增统一最终结果渲染函数

**Files**

- Modify: `ui/pages.py`

**步骤**

1. 新增 `render_final_calorie_and_advice(calorie_result, advice_result)`。
2. `calorie_result` 存在时只渲染一次 `calorie_result_card(...)`。
3. `advice_result.status == "success"` 时显示：

```text
生成完毕
Model 建议已完成。
Model 饮食建议
```

4. `advice_result.status != "success"` 时显示：

```text
失败：<错误原因>
已展示本地规则建议。
本地规则建议
```

5. 不在其他位置重复渲染最终建议卡片。

### Task 3：生成后重新渲染

**Files**

- Modify: `ui/pages.py`

**步骤**

1. 点击“计算热量并生成建议”后保持原有业务顺序：
   - 计算热量。
   - 流式生成建议。
   - 保存历史记录。
   - 保存 Model 日志。
   - 写入 `st.session_state.calorie_result`。
   - 写入 `st.session_state.advice_result`。
2. 写入状态后调用 `st.rerun()`。
3. 页面重新运行后只调用 `render_final_calorie_and_advice(...)` 输出最终结果。

### Task 4：补充防回归测试

**Files**

- Modify: `tests/test_app_contract.py`

**步骤**

1. 使用 AST 辅助函数读取 `render_model_advice_stream()` 函数体。
2. 断言流式函数体内不包含：
   - `workflow_state_strip(`
   - `Model 饮食建议`
   - `本地规则建议`
3. 断言 `ui/pages.py` 包含 `render_final_calorie_and_advice(...)`。
4. 断言 `recognition_page()` 使用 `st.rerun()` 防止同轮重复渲染。

### Task 5：文档同步

**Files**

- Modify: `doc/10-阶段开发计划.md`
- Modify: `doc/开发阻塞记录.md`

**步骤**

1. 在阶段开发计划中追加“阶段十二：修复 Model 建议生成后重复渲染”。
2. 执行完成后填写：
   - `已完成`
   - `完成提交`
   - `验证证据`
   - `阻塞记录`
3. 在阻塞记录中追加阶段十二验收记录。
4. 如真实 Model API 失败，只记录非敏感错误原因，不记录真实 Key 或完整敏感 URL。

---

## 4. 验证命令

自动化验证：

```powershell
pytest -q
ruff check .
python -m py_compile app.py services/*.py train/*.py ui/*.py tests/*.py
```

文本检查：

```powershell
rg -n "workflow_state_strip\\(|Model 饮食建议|本地规则建议" ui/pages.py tests/test_app_contract.py
```

预期：

- `render_model_advice_stream()` 内不再出现最终建议卡片。
- `Model 饮食建议` 只由最终结果渲染函数输出。
- `workflow_state_strip()` 不在流式函数内调用。
- 所有自动化测试通过。

---

## 5. Browser-use 验收

启动 Streamlit：

```powershell
streamlit run app.py --server.address=127.0.0.1 --server.port=8501 --server.headless=true
```

PC 验收：

1. 使用 `$browser-use` 打开 `http://127.0.0.1:8501`。
2. 上传 `D:\白云\下\ai\end\testData\900fa129383aecfbebd0f257ee1ca668.jpg`。
3. 点击 `开始识别`。
4. 点击 `计算热量并生成建议`。
5. 检查：
   - 图片预览显示。
   - 识别结果和 Top-3 显示。
   - 估算热量显示一次。
   - `生成完毕` 最终状态显示一次。
   - `Model 饮食建议` 最终卡片显示一次。
   - 不再重复显示整组状态说明。

移动端模拟验收：

1. 使用 390×844 视口。
2. 检查底部导航无横向溢出。
3. 生成建议后检查最终结果仍只显示一组。

验收后停止 Streamlit 服务。

---

## 6. 提交计划

提交信息：

```text
阶段十二：修复生成结果重复渲染，较上次统一 Model 建议最终展示入口
```

提交前确认：

- `git status` 不包含 `.env`、数据库、数据集、模型权重、测试图片或缓存。
- 只提交本阶段代码、测试和 Markdown 文档。

---

## 7. 验收标准

- `Model 饮食建议` 最终结果只显示一次。
- `估算热量` 结果只显示一次。
- `生成完毕` 不再与重复状态说明块反复出现。
- 流式生成过程仍可见。
- 成功时显示 `生成完毕`。
- 失败时显示 `失败：<错误原因>`。
- 本地规则建议只在失败或 fallback 时显示。
- 历史记录仍保存最终建议文本。
- 页面内 Model 配置入口不受影响。
- 真实图片上传、识别、热量估算、建议生成流程不受影响。
- 自动化测试通过。
- `$browser-use` PC 与 390×844 移动端模拟验收通过。

---

## 8. Assumptions

- 本阶段只修复重复渲染问题。
- 最终展示采用“持久结果区单一入口”方案。
- 流式函数只负责生成过程中的临时 UI，不负责最终结果 UI。
- 如果真实 Model API 返回失败，继续显示失败原因和本地规则建议。
