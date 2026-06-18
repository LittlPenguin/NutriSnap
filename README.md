# NutriSnap 轻食记录

NutriSnap 是一个基于 Streamlit、PyTorch 和 SQLite 的食物图像识别与热量估算系统。用户上传食物图片后，系统使用本地 ResNet18 模型识别食物类别，结合重量输入和每 100g 热量表计算估算热量，并可调用 OpenAI 兼容 Model API 生成饮食建议。

本项目用于课程设计演示。页面中的热量结果仅供饮食记录参考，不作为医学或营养诊断依据。

## 项目特性

- Streamlit 多页面 Web 应用，兼容 PC 浏览器和移动端浏览器
- 本地 ResNet18 食物分类推理，返回类别、置信度和 Top-3 结果
- 基于食物类别、重量和热量表的估算热量计算
- OpenAI 兼容 Model API 饮食建议，支持本地规则降级
- SQLite 历史记录、热量表和统计分析
- 支持 Food-101 子集数据准备、训练和评估脚本

## 技术栈

- Python
- Streamlit
- PyTorch
- torchvision
- SQLite
- Pillow
- Pandas / NumPy
- OpenAI 兼容 Model API

## 目录结构

```text
app.py
services/                核心业务逻辑
ui/                      页面与组件
train/                   数据准备、训练、评估脚本
data/                    热量种子数据与本地数据库
models/                  本地模型权重与类别文件
tests/                   自动化测试
doc/                     项目文档
```

## 环境准备

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

如需运行测试和静态检查，再安装开发依赖：

```powershell
pip install -r requirements-dev.txt
```

## 配置说明

复制 `.env.example` 为 `.env`，按需填写：

```text
OPENAI_API_KEY=
OPENAI_BASE_URL=
OPENAI_MODEL=gpt-5
NUTRISNAP_DEMO_MODE=false
```

说明：

- `OPENAI_API_KEY`：OpenAI 兼容接口密钥，可留空；留空时页面建议功能会自动降级到本地规则建议。
- `OPENAI_BASE_URL`：兼容接口地址，可为空。
- `OPENAI_MODEL`：建议模型名称，默认 `gpt-5`。
- `NUTRISNAP_DEMO_MODE`：设为 `true` 时，识别页会返回固定演示结果，适合没有本地模型权重时演示页面流程。

页面中也可以临时填写 OpenAI 配置。页面配置优先级高于 `.env`，但只保存在当前 Streamlit 会话，不会写入数据库或 Git。

## 启动项目

```powershell
streamlit run app.py
```

启动后在浏览器打开本地 Streamlit 地址即可。

如果本地缺少 `models/food_resnet18.pth` 或 `models/class_names.json`：

- 识别页会提示模型未加载
- 不会导致应用崩溃
- 可先开启 `NUTRISNAP_DEMO_MODE=true` 进行课程演示

## 页面功能

- `食物识别`：上传图片，执行 ResNet18 分类，输入重量并生成热量估算与饮食建议
- `历史记录`：查看历史识别记录与建议结果
- `热量表`：查看支持类别、默认份量和每 100g 热量
- `统计分析`：查看历史记录统计结果

## 模型说明

项目中的图片识别模型是本地 PyTorch ResNet18，不是 GPT。

职责划分：

- ResNet18：识别上传图片中的食物类别
- 热量模块：根据识别类别、用户输入重量和热量表计算估算热量
- OpenAI 兼容 Model API：根据食物名称、重量、估算热量和用户目标生成中文饮食建议

当前代码中的类别配置来自 `services/schemas.py` 和 `models/class_names.json`。训练和推理必须使用一致的类别顺序文件。

## 数据准备与模型训练

项目使用 Food-101 子集进行训练。训练前需要先准备目录结构正确的数据集，再运行训练和评估脚本。

### 1. 准备 Food-101 子集

如果本地已经有 Food-101 原始图片目录：

```powershell
.\.venv\Scripts\python.exe train\prepare_food101_subset.py `
  --source-root dataset\food101_raw\food-101\images `
  --output-root dataset\food101_subset_25_500 `
  --limit-per-class 500 `
  --seed 42 `
  --report-json dataset\food101_subset_25_500_report.json
```

如果希望脚本先尝试下载 Food-101 原始数据：

```powershell
.\.venv\Scripts\python.exe train\prepare_food101_subset.py `
  --download `
  --raw-root dataset\food101_raw `
  --output-root dataset\food101_subset `
  --limit-per-class 200 `
  --seed 42 `
  --report-json dataset\food101_subset_report.json
```

说明：

- `--limit-per-class` 控制每类最多取多少张图
- 数据会按 `70% / 15% / 15%` 划分为 `train / val / test`
- 输出目录中会自动生成 `class_names.json`

### 2. 验证已准备好的数据集

```powershell
.\.venv\Scripts\python.exe train\prepare_food101_subset.py `
  --validate-only `
  --output-root dataset\food101_subset_25_500 `
  --report-json dataset\food101_subset_25_500_report.json
```

验收报告会检查：

- `train/val/test` 是否齐全
- 每个类别目录是否存在且非空
- `class_names.json` 是否和训练配置一致

### 3. 训练 ResNet18 模型

```powershell
.\.venv\Scripts\python.exe train\train_model.py `
  --dataset-root dataset\food101_subset_25_500 `
  --output-model models\food_resnet18.pth `
  --output-classes models\class_names.json `
  --epochs 8 `
  --batch-size 16 `
  --learning-rate 0.001 `
  --num-workers 0
```

参数说明：

- `--dataset-root`：训练数据目录，必须包含 `train/` 和 `val/`
- `--output-model`：训练后模型权重输出路径
- `--output-classes`：类别顺序文件输出路径
- `--epochs`：训练轮数
- `--batch-size`：批大小
- `--learning-rate`：学习率
- `--num-workers`：DataLoader 工作进程数，Windows 本地建议使用 `0`

默认训练方式是迁移学习并冻结 ResNet18 主干，仅训练最后的分类层。

如果要解冻主干一起训练：

```powershell
.\.venv\Scripts\python.exe train\train_model.py `
  --dataset-root dataset\food101_subset_25_500 `
  --output-model models\food_resnet18.pth `
  --output-classes models\class_names.json `
  --epochs 8 `
  --batch-size 16 `
  --learning-rate 0.0001 `
  --unfreeze-backbone `
  --num-workers 0
```

### 4. 评估模型

```powershell
.\.venv\Scripts\python.exe train\evaluate_model.py `
  --dataset-root dataset\food101_subset_25_500 `
  --model-path models\food_resnet18.pth `
  --class-names-path models\class_names.json `
  --batch-size 16 `
  --num-workers 0
```

评估结果会输出：

- `accuracy`：Top-1 准确率
- `top3_accuracy`：Top-3 准确率
- `sample_count`：测试样本数量
