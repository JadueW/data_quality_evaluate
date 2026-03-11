import os.path
import matplotlib.pyplot as plt

plt.rcParams.update({
    # --- 字体设置 ---
    'font.family': 'serif',
    'font.serif': ['Times New Roman', 'DejaVu Serif', 'serif'],
    'mathtext.fontset': 'stix',
    'mathtext.rm': 'Times New Roman',
    'mathtext.it': 'Times New Roman:italic',
    'mathtext.bf': 'Times New Roman:bold',
    'axes.unicode_minus': False,

    # --- 字号设置---
    'font.size': 16,
    'axes.titlesize': 13,
    'axes.labelsize': 13,
    'axes.labelweight': 'bold',
    'xtick.labelsize': 12,
    'ytick.labelsize': 12,
    'legend.fontsize': 12,
    'legend.title_fontsize': 10,
    'figure.titlesize': 11,

    # --- 线条和标记 ---
    'lines.linewidth': 1.2,
    'lines.markersize': 4,
    'lines.markeredgewidth': 0.5,

    # 坐标轴样式
    'axes.spines.top': False,
    'axes.spines.right': False,
    'axes.linewidth': 1.0,

    # --- 刻度样式 ---
    'xtick.major.width': 0.8,
    'ytick.major.width': 0.8,
    'xtick.minor.width': 0.4,
    'ytick.minor.width': 0.4,
    'xtick.major.size': 3,
    'ytick.major.size': 3,
    'xtick.minor.size': 1.5,
    'ytick.minor.size': 1.5,
    'xtick.direction': 'in',
    'ytick.direction': 'in',
    'xtick.top': False,
    'ytick.right': False,

    # --- 图例 ---
    'legend.frameon': True,
    'legend.edgecolor': 'black',
    'legend.fancybox': False,
    'legend.borderpad': 0.4,
    'legend.handlelength': 1.5,

    # --- 输出 ---
    'figure.dpi': 300,
    'savefig.dpi': 600,
    'savefig.format': 'pdf',
    'savefig.bbox': 'tight',
    'savefig.pad_inches': 0.02,

    'axes.prop_cycle': plt.cycler(color=[
        '#1A2CA3', '#C40C0C', '#2e7d32', '#f57c00',
        '#6a1b9a', '#00695c', '#ad1457', '#455a64',
    ]),
})

if __name__ == '__main__':
    from pipeline import batch_evaluate_dataset

    RAW_DATA_DIR = '../data/raw/'
    # compare_data_dirs = [data_dir for data_dir in os.listdir(RAW_DATA_DIR) if data_dir.__contains__("对照") and data_dir.__contains__("大白")][0:1]
    experiment_data_dirs = [data_dir for data_dir in os.listdir(RAW_DATA_DIR) if data_dir.__contains__("实验")and data_dir.__contains__("大白")][0:1]

    # batch_evaluate_dataset(RAW_DATA_DIR,compare_data_dirs)
    batch_evaluate_dataset(RAW_DATA_DIR,experiment_data_dirs)
