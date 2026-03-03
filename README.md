# 数据质量评估系统

## 项目简介

本系统是一个完整的数据质量评估解决方案，支持多种数据格式的加载、智能预处理、多维度质量指标分析，并自动生成专业的 PDF 评估报告。

### 主要特性

- 🎯 **多格式支持**：支持 `.wl` 、`.edf`、`.dat` 等多种脑电数据格式
- 🧠 **智能预处理**：陷波滤波、带通滤波、坏道检测、重参考等完整预处理流水线
- 📊 **多维度评估**：幅度、标准差、信噪比、阻抗等多个质量指标
- 📈 **TDigest 统计**：基于 TDigest 算法的概率统计，节省内存且精度高
- 🎨 **可视化分析**：电极拓扑图、信号趋势图等多角度可视化
- 📄 **自动报告**：生成包含完整分析结果的专业 PDF 报告
- ⚡ **智能加载**：根据硬件资源自动选择最优数据加载策略

---

## 项目结构

```text
data_quality_evaluate/
│
├── README.md
├── requirements.txt              # 项目依赖
│
├── config/                       # 配置文件目录
│   ├── default.json             # 默认配置
│   └── report_template.json     # 报告模板配置
│
├── data/                         # 数据目录
│   ├── raw/                     # 原始数据（按被试组织）
│   │   └── [被试文件夹]/
│   │       ├── *.wl / *.edf / *.dat    # 数据文件
│   │       ├── *impedence*            # 阻抗文件
│   │       └── *电极类型*              # 电极映射文件
│   ├── processed/               # 预处理结果（可选）
│   └── statistical/             # 统计结果（可选）
│
├── results/                      # 结果输出目录
│   └── [被试文件夹]/
│       ├── elec_mapping.png              # 电极拓扑图
│       ├── signal_trends_mean.png        # 信号均值趋势图
│       ├── signal_trends_std.png         # 信号标准差趋势图
│       └── data_quality_report.pdf       # 质量评估报告
│
└── src/                          # 源代码目录
    ├── __init__.py
    ├── pipline.py                # 主流程入口，协调整个评估流程
    ├── analyse.py                # 数据分析接口（统计/SNR分析）
    │
    ├── data_io/                  # 数据加载模块
    │   ├── __init__.py
    │   └── dataParse.py          # 多格式数据解析器
    │                               # 支持 wl/edf/dat 格式
    │                               # 智能加载策略（全量/合并/分块）
    │
    ├── preprocessing/            # 预处理模块
    │   └── preprocessor.py       # 信号预处理流水线
    │                               # - group(): 电极分组（uCortex/PSE）
    │                               # - notch_filter(): 陷波滤波
    │                               # - pass_filter(): 带通滤波
    │                               # - bad_check(): 坏道检测
    │                               # - re_reference(): 重参考
    │
    ├── metrics/                  # 指标计算模块
    │   ├── __init__.py
    │   ├── statistics.py         # 基于 TDigest 的概率统计
    │   ├── calc_snr.py           # 信噪比计算（LFP方法）
    │   └── statisticsAggregator.py  # 跨窗口统计聚合
    │
    ├── report/                   # 报告生成模块
    │   ├── extractReportFeatures.py  # 报告特征提取
    │   └── report_generator.py      # PDF 报告生成器
    │
    ├── visualize/                # 可视化模块
    │   ├── __init__.py
    │   └── visualizer.py         # 绘图工具类
    │                               # - plot_ch_win_mean(): 均值趋势图
    │                               # - plot_ch_win_std(): 标准差趋势图
    │                               # - plot_electrode_topology_mask(): 拓扑图
    │
    └── utils/                    # 工具模块
        ├── __init__.py
        ├── hardware_resources.py     # 硬件资源检测（CPU/内存/磁盘）
        ├── filesProcess.py           # 文件处理工具
        ├── ECOGLoader.py             # 旧版数据加载器
        ├── brpylib.py                # Blackrock (.nsX) 格式支持
        └── importrhdutilities.py     # Intan RHD (.wl) 格式支持
```

---

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 准备数据

在 `data/raw/` 下创建被试文件夹，包含：
- 数据文件（`.wl` / `.edf` / `.dat`）
- 阻抗文件（文件名包含 `impedence`）
- 电极映射文件（文件名包含电极类型）

### 3. 运行评估
在pipeline.py文件中修改确认数据文件夹、输出路径等位置后
```bash
cd src
python pipline.py
```

### 4. 查看结果

评估完成后，在 `results/` 对应文件夹中查看：
- `data_quality_report.pdf` - 完整质量评估报告
- `elec_mapping.png` - 电极拓扑图
- `signal_trends_mean.png` - 信号均值趋势图
- `signal_trends_std.png` - 信号标准差趋势图

---


## 数据流程

```
原始数据文件夹
    ↓
[DataParse] 智能加载（全量/合并/分块）
    ↓
批次数据迭代器
    ↓
[Analyse] 分窗口 + [Preprocessor] 预处理
    ├─ notch_filter() (50,100,150,200Hz)
    ├─ pass_filter() (1-200Hz)
    ├─ bad_check() (std>100 or 阻抗>1MΩ)
    └─ re_reference() (平均参考)
    ↓
[Statistics] TDigest 概率统计
[CalcSnr] 信噪比计算
    ↓
[StatisticsAggregator] 跨窗口聚合
    ↓
[ExtractReportFeatures] 特征提取
    ├─ 幅度统计 (min/max/mean/median/variability/百分位数)
    ├─ 标准差统计
    ├─ SNR 统计
    └─ 阻抗统计
    ↓
[Visualizer] 生成可视化图像
    ↓
[PDFReportGenerator] 生成 PDF 报告
    ↓
结果文件夹
```
