## 数据质量评估系统

### 1. 项目结构
```text
data_quality_evaluate/
│
├── README.md
├── requirements.txt
├── config/
│   ├── default.json            # 数据加载和预处理等可能用到的外部配置文件
│   └── report_template.json    # 生成模板文件可能用到的配置文件，如字体大小、边框、logo等
│
├── data/
│   ├── raw/                # 原始数据
│   ├── processed/          # 预处理结果
│   └── statistical/        # 统计结果
│
│── results/
│   ├── 小黑20260114第二只001对照组       # example，和输入文件夹的名字保持一直，便于对应  
│        ├── elec_mapping.png          # 电极拓扑图
│        ├── signal_trends_mean.png    # 信号变化趋势图1
│        ├── signal_trends_std.png     # 信号变化趋势图2
│        ├── data_quality_report.pdf   # 基于模板生成的pdf文件
│
├── src/
│   ├── io/
│   │   ├── loader.py       # wl/edf/dat 解析
│   │   └── metadata.py
│   │
│   ├── preprocessing/      # example
│   │   ├── xxx.py
│   │   ├── xxx.py
│   │   ├── xxx.py
│   │   └── xxx.py
│   │
│   ├── metrics/
│   │   ├── statistics.py   # mean/std
│   │   ├── snr.py
│   │   
│   │
│   ├── aggregation/
│   │   └── all_statistics.py
│   │
│   ├── report/                   # example
│   │   ├── report_builder.py
│   │   ├── template.py
│   │   └── visualization.py
│   │
│   └── pipeline.py         # 主流程入口
```


