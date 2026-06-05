# NutriSnap 轻食记录

NutriSnap 是一个基于 Streamlit 与迁移学习的食物图像识别与热量估算系统。用户上传食物图片后，系统通过 ResNet18 食物分类模型识别类别，结合用户输入重量和 SQLite 热量表计算估算热量，并可调用 GPT-5 API 生成饮食建议。

本系统用于课程设计演示，热量结果仅供饮食记录参考，不作为医学或营养诊断。

## 功能

- 图片上传与预览
- ResNet18 食物分类推理
- Top-3 预测结果展示
- 基于重量和每 100g 热量表的估算热量
- GPT-5 饮食建议与本地规则降级
- SQLite 历史记录
- 食物热量表查询
- 近 7 日统计分析
- PC 与移动端浏览器兼容的 Streamlit 页面

## 运行

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
streamlit run app.py
```

复制 `.env.example` 为 `.env` 后，可配置：

```text
OPENAI_API_KEY=
OPENAI_MODEL=gpt-5
NUTRISNAP_DEMO_MODE=false
```

没有模型权重时，系统会显示模型未加载；如需课程演示示例结果，可将 `NUTRISNAP_DEMO_MODE=true`。

## 测试

```powershell
pip install -r requirements-dev.txt
pytest
ruff check .
```

## 模型训练

一期支持 Food-101 子集 12 类。训练脚本位于 `train/`，训练输出的模型权重默认保存到 `models/food_resnet18.pth`，该文件不提交。
