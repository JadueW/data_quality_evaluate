# 数据质量评估系统

## 项目简介

本系统是一个完整的数据质量评估解决方案，支持多种数据格式的加载、智能预处理、多维度质量指标分析，并自动生成专业的 PDF 评估报告。

### 主要特性

- 🎯 **多格式支持**：支持 `.wl` 、`.edf`、`.dat` 等多种脑电数据格式
- 🧠 **智能预处理**：陷波滤波、带通滤波、坏道检测、重参考等完整预处理流水线
- 📊 **多维度评估**：幅度、标准差、信噪比、阻抗等多个质量指标
- 📈 **TDigest 统计**：基于 TDigest 算法的概率统计，节省内存且精度高
- 🎨 **可视化分析**：电极拓扑图、信号趋势图（自动选择时间单位）等多角度可视化
- 📄 **自动报告**：生成包含完整分析结果的专业 PDF 报告
- ⚡ **智能加载**：根据硬件资源自动选择最优数据加载策略
- ✅ **数据质量控制**：自动过滤坏窗口和坏通道，确保统计指标只基于有效数据

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
    ├── pipeline.py                # 主流程入口，协调整个评估流程
    ├── analyse.py                 # 数据分析接口（统计/SNR分析/线噪声检测）
    │
    ├── data_io/                   # 数据加载模块
    │   ├── __init__.py
    │   └── dataParse.py           # 多格式数据解析器
    │                                # 支持 wl/edf/dat 格式
    │                                # 智能加载策略（全量/合并/分块）
    │
    ├── preprocessing/             # 预处理模块
    │   └── preprocessor.py        # 信号预处理流水线
    │                                # - group(): 电极分组（uCortex/PSE）
    │                                # - notch_filter(): 陷波滤波（50,100,150,200Hz）
    │                                # - pass_filter(): 带通滤波（1-200Hz）
    │                                # - bad_check(): 坏道检测（std>100）
    │                                # - re_reference(): 重参考
    │                                # - line_noise_detect(): 线噪声检测
    │
    ├── metrics/                   # 指标计算模块
    │   ├── __init__.py
    │   ├── statistics.py          # 窗口级统计（Welford + TDigest）
    │   ├── welford_statistics.py  # Welford 在线统计算法
    │   ├── calc_snr.py            # 信噪比计算（LFP方法）
    │   └── statisticsAggregator.py # 跨窗口统计聚合（保存掩码）
    │
    ├── report/                    # 报告生成模块
    │   ├── extractReportFeatures.py # 报告特征提取（分离绘图和统计数据）
    │   └── report_generator.py    # PDF 报告生成器
    │
    ├── visualize/                 # 可视化模块
    │   ├── __init__.py
    │   └── visualizer.py          # 绘图工具类
    │                                # - plot_ch_win_mean(): 均值趋势图（自动时间单位）
    │                                # - plot_ch_win_std(): 标准差趋势图（自动时间单位）
    │                                # - plot_electrode_topology_mask(): 拓扑图
    │
    └── utils/                     # 工具模块
        ├── __init__.py
        ├── hardware_resources.py  # 硬件资源检测（CPU/内存/磁盘）
        ├── filesProcess.py        # 文件处理工具
        ├── ECOGLoader.py          # 数据加载器
        ├── brpylib.py             # Blackrock (.nsX) 格式支持
        └── importrhdutilities.py  # Intan RHD (.wl) 格式支持
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
python pipeline.py
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
[Analyse] 分窗口处理 + [Preprocessor] 预处理
    ├─ handle_statistics(): 5秒窗口，无重叠
    │   ├─ group(): 电极分组（uCortex: 128ch/group, PSE: 4ch/group）
    │   ├─ notch_filter(): 陷波滤波（50,100,150,200Hz）
    │   ├─ pass_filter(): 带通滤波（1-200Hz）
    │   ├─ bad_check(): 坏道检测（std>100）→ win_check_mask, ch_check_mask
    │   └─ re_reference(): 平均参考
    │
    ├─ handle_snr(): 60秒窗口，重叠30秒
    │   └─ compute_single_window_snr(): SNR计算（LFP方法）
    │
    └─ handle_line_noise_detection(): 1秒窗口，最多30秒
        └─ line_noise_detect(): 线噪声检测（FFT分析）
    ↓
[Statistics] 窗口级统计
    ├─ WelfordArray: 在线计算均值/标准差
    └─ TDigest: 计算百分位数
    ↓
[StatisticsAggregator] 跨窗口聚合
    ├─ 保存掩码: all_win_check_mask, all_ch_check_mask, all_win_ch_check_mask
    ├─ 保存统计: all_win_welford, all_win_tdigest
    └─ 跨窗口合并 TDigest
    ↓
[ExtractReportFeatures] 特征提取（分离绘图和统计）
    ├─ compute_ch_win_mean():
    │   ├─ all_group_ch_win_means: 所有窗口的所有通道 → 用于绘图
    │   └─ valid_group_ch_win_means: 有效窗口的好通道 → 用于统计
    │
    ├─ compute_ch_win_std():
    │   ├─ all_group_ch_win_stds: 所有窗口的所有通道 → 用于绘图
    │   └─ valid_group_ch_win_stds: 有效窗口的好通道 → 用于统计
    │
    ├─ _compute_cross_win(): 跨窗口合并 TDigest（只合并有效窗口）
    └─ generate_report_statistics():
        ├─ amp: 幅度统计（基于 TDigest）
        ├─ std: 标准差统计（基于 valid_group_ch_win_stds）
        ├─ mean: 均值统计（基于 valid_group_ch_win_means）
        └─ impedence: 阻抗统计
    ↓
[Visualizer] 生成可视化图像
    ├─ plot_ch_win_mean(): 均值趋势图（自动选择时间单位：s/min）
    ├─ plot_ch_win_std(): 标准差趋势图（自动选择时间单位：s/min）
    └─ plot_electrode_topology_mask(): 电极拓扑图
    ↓
[PDFReportGenerator] 生成 PDF 报告
    ↓
结果文件夹
```
