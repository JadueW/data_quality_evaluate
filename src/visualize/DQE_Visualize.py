import os
import json
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats
import warnings

plt.style.use('default')
sns.set_theme(style="whitegrid", palette="deep")
warnings.filterwarnings("ignore")

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

    # --- 网格线设置  ---
    'axes.grid': True,
    'grid.linewidth': 1.5,
    'grid.color': 'gray',
    'grid.alpha': 0.3,
    'grid.linestyle': '-',

    # --- 线条和标记 ---
    'lines.linewidth': 1.2,
    'lines.markersize': 4,
    'lines.markeredgewidth': 1,

    # --- 边框与刻度加粗 ---
    'xtick.major.width': 3,
    'ytick.major.width': 3,
    'xtick.minor.width': 3,
    'ytick.minor.width': 3,

    # 坐标轴样式
    'axes.spines.top': False,
    'axes.spines.right': False,
    # 'axes.linewidth': 1.0,

    # --- 刻度样式 ---
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
    'savefig.dpi': 300,
    'savefig.format': 'pdf',
    'savefig.bbox': 'tight',
    'savefig.pad_inches': 0.02,

    'axes.prop_cycle': plt.cycler(color=[
        '#1A2CA3', '#C40C0C', '#2e7d32', '#f57c00',
        '#6a1b9a', '#00695c', '#ad1457', '#455a64',
    ]),
})



raw_dir = '../../results'
compare_g = [dir_name for dir_name in os.listdir(raw_dir) if dir_name.__contains__("对照") and not dir_name.__contains__("大白")]
exper_g = [dir_name for dir_name in os.listdir(raw_dir) if dir_name.__contains__("实验") and not dir_name.__contains__("大白")]

compare_group_json = [os.path.join(raw_dir,file_path,'pdf_results_group0.json') for file_path in compare_g]
exper_group_json = [os.path.join(raw_dir,file_path,'pdf_results_group0.json') for file_path in exper_g]

def load_data(file_paths, group_name):
    data_list = []
    for path in file_paths:
        with open(path, 'r', encoding='utf-8') as f:
            d = json.load(f)
            data_list.append({
                'Group': group_name,
                'File': os.path.basename(path),
                'SNR_Avg': d['snr_range']['avg'],
                'Impedance_Avg': d['impedence_range']['avg'],
                'STD_Avg': d['std']['avg'],
                'Bad_Ratio': d['bad_ratio'],
                "Variability": d['amp']['variability']
            })
    return pd.DataFrame(data_list)


def plot_line(compare_json_df, exper_json_df):
    fig, axes = plt.subplots(2, 2, figsize=(12, 12))
    fig.patch.set_facecolor('white')

    axes = axes.flatten()

    # 1.SNR
    sns.lineplot(data=compare_json_df, x=compare_json_df.index, y='SNR_Avg',
                 marker='o', label='C', ax=axes[0])
    sns.lineplot(data=exper_json_df, x=exper_json_df.index, y='SNR_Avg',
                 marker='s', label='E', ax=axes[0])

    ticks = axes[0].get_xticks()
    axes[0].set_xticklabels([int(t) + 1 for t in ticks])
    axes[0].set_title('Average SNR Comparison')
    axes[0].set_xlabel('Num.')
    axes[0].set_ylabel('SNR (dB)')

    # 2.Impedence
    sns.lineplot(data=compare_json_df, x=(compare_json_df.index+1), y='Impedance_Avg',
                 marker='o', label='C', ax=axes[1])
    sns.lineplot(data=exper_json_df, x=(exper_json_df.index+1), y='Impedance_Avg',
                 marker='s', label='E', ax=axes[1])
    axes[1].set_title('Average Impedance Comparison')
    axes[1].set_xlabel('Num.')
    axes[1].set_ylabel('Impedance (kOhms)')

    # 3.STD
    sns.lineplot(data=compare_json_df, x=(compare_json_df.index+1), y='STD_Avg',
                 marker='o', label='C', ax=axes[2])
    sns.lineplot(data=exper_json_df, x=(exper_json_df.index+1), y='STD_Avg',
                 marker='s', label='E', ax=axes[2])
    axes[2].set_title('Average STD Comparison')
    axes[2].set_xlabel('Num.')
    axes[2].set_ylabel('Signal STD')

    # 4.MEAN
    sns.lineplot(data=compare_json_df, x=(compare_json_df.index+1), y='AMP_Avg',
                 marker='o', label='C', ax=axes[3])
    sns.lineplot(data=exper_json_df, x=(exper_json_df.index+1), y='AMP_Avg',
                 marker='s', label='E', ax=axes[3])
    axes[3].set_title('Average AMP Comparison')
    axes[3].set_xlabel('Num.')
    axes[3].set_ylabel('Signal MEAN')

    plt.tight_layout()

    plt.savefig("./line_plot.png", dpi=300)
    plt.show()


def plot_line_separate(compare_json_df, exper_json_df):
    plot_configs = [
        {'y_col': 'SNR_Avg', 'title': 'Average SNR Comparison', 'ylabel': 'SNR (dB)',
         'filename': './line_plot_snr.png'},
        {'y_col': 'Impedance_Avg', 'title': 'Average Impedance Comparison', 'ylabel': 'Impedance (kOhms)',
         'filename': './line_plot_impedance.png'},
        {'y_col': 'STD_Avg', 'title': 'Average STD Comparison', 'ylabel': 'Signal STD',
         'filename': './line_plot_std.png'},
        {'y_col': 'Variability', 'title': 'Variability Comparison', 'ylabel': 'Signal Variability',
         'filename': './line_plot_Variability.png'}
    ]

    for config in plot_configs:
        fig, ax = plt.subplots(figsize=(8, 6))
        fig.patch.set_facecolor('white')

        sns.lineplot(data=compare_json_df, x=(compare_json_df.index+1), y=config['y_col'],
                     marker='o', label='C', ax=ax)
        sns.lineplot(data=exper_json_df, x=(exper_json_df.index+1), y=config['y_col'],
                     marker='s', label='E', ax=ax)

        ax.set_title(config['title'],fontsize=18)
        ax.set_xlabel('Num.',fontsize=16)
        ax.set_ylabel(config['ylabel'],fontsize=16)
        # ax.xaxis.get_major_locator().set_params(integer=True)

        plt.tight_layout()

        plt.savefig(config['filename'], dpi=300)

        plt.show()

        plt.close(fig)


def plot_box_stat_separate(compare_json_df, exper_json_df):
    compare_json_df['Group'] = 'C'
    exper_json_df['Group'] = 'E'
    df_combined = pd.concat([compare_json_df, exper_json_df], ignore_index=True)

    metrics = [
        ('SNR_Avg', 'Average SNR (dB)', 'SNR Comparison', './box_stat_snr.png'),
        ('Impedance_Avg', 'Average Impedance (kOhms)', 'Impedance Comparison', './box_stat_impedance.png'),
        ('STD_Avg', 'Signal STD', 'STD Comparison', './box_stat_std.png'),
        ('Variability', 'Signal Variability', 'Variability Comparison', './box_stat_variability.png')
    ]

    for metric, ylabel, title, filename in metrics:

        fig, ax = plt.subplots(figsize=(8, 6))
        fig.patch.set_facecolor('white')

        sns.boxplot(x='Group', y=metric, data=df_combined, ax=ax,
                    width=0.4, boxprops=dict(alpha=0.3), fliersize=0)

        sns.stripplot(x='Group', y=metric, data=df_combined, ax=ax,
                      size=7, jitter=0.15, alpha=0.8, palette=["#1f77b4", "#d62728"], hue='Group', legend=False)

        group1 = df_combined[df_combined['Group'] == 'C'][metric]
        group2 = df_combined[df_combined['Group'] == 'E'][metric]

        stat, p_val = stats.mannwhitneyu(group1, group2, alternative='two-sided')

        if p_val < 0.001:
            sig = '***'
        elif p_val < 0.01:
            sig = '**'
        elif p_val < 0.05:
            sig = '*'
        else:
            sig = 'ns'

        y_max = df_combined[metric].max()
        y_min = df_combined[metric].min()
        y_range = y_max - y_min
        if y_range == 0: y_range = 1

        h = y_range * 0.05
        text_y = y_max + y_range * 0.08

        ax.plot([0, 0, 1, 1], [y_max + h, text_y, text_y, y_max + h], lw=1.2, c='black')
        ax.text(0.5, text_y + y_range * 0.02, f'{sig}\n(p={p_val:.3f})', ha='center', va='bottom', color='black')

        ax.set_ylim(y_min - y_range * 0.05, text_y + y_range * 0.2)

        ax.set_ylabel(ylabel,fontsize=16)
        ax.set_xlabel('')
        ax.set_title(title,fontsize=18)
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)

        plt.tight_layout()

        plt.savefig(filename, dpi=300)

        plt.show()

        plt.close(fig)


if __name__ == '__main__':
    compare_json_df = load_data(compare_group_json, "C")
    exper_json_df = load_data(exper_group_json, "E")
    plot_line_separate(compare_json_df, exper_json_df)
    plot_box_stat_separate(compare_json_df, exper_json_df)

