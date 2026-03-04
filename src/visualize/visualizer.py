"""
可视化
"""
import matplotlib.pyplot as plt
from matplotlib.patches import Circle
import matplotlib.patches as mpatches
import numpy as np

class Visualizer:
    """ 绘图的工具类
        用来绘制电极拓扑图、以及信号变化趋势图（mean，std）
     """
    @classmethod
    def plot_ch_win_mean(cls,all_group_ch_win_means,group_id=None,offset=5,**kwargs):
        if group_id is None:
            group_id = list(all_group_ch_win_means.keys())[0]

        ch_win_means = all_group_ch_win_means[group_id]
        n_channels = len(ch_win_means)
        n_windows = len(ch_win_means[0])

        fig, ax = plt.subplots(figsize=(12, 8))

        for ch_idx in range(n_channels):
            means = np.array(ch_win_means[ch_idx])
            offset_values = means + ch_idx * offset
            ax.plot(range(n_windows), offset_values, linewidth=0.8, alpha=0.7)

        ax.set_xlabel('Window Index', fontsize=12)
        ax.set_ylabel('Channel (with offset)', fontsize=12)
        ax.set_title(f'Channel Mean Trends Over Windows - Group: {group_id}', fontsize=14)
        ax.set_yticks([i * offset for i in range(n_channels)])
        ax.set_yticklabels([f'Ch{i}' for i in range(n_channels)])

        plt.tight_layout()
        plt.savefig(kwargs.get('save_path',"./signal_trends_mean.png"),dpi=600)

        return fig

    @classmethod
    def plot_ch_win_std(cls,all_group_ch_win_std,group_id=None,offset=5,**kwargs):
        if group_id is None:
            group_id = list(all_group_ch_win_std.keys())[0]

        ch_win_std = all_group_ch_win_std[group_id]
        n_channels = len(ch_win_std)
        n_windows = len(ch_win_std[0])

        fig, ax = plt.subplots(figsize=(12, 8))

        for ch_idx in range(n_channels):
            std = np.array(ch_win_std[ch_idx])
            offset_values = std + ch_idx * offset
            ax.plot(range(n_windows), offset_values,linewidth=0.8, alpha=0.7)

        ax.set_xlabel('Window Index', fontsize=12)
        ax.set_ylabel('Channel (with offset)', fontsize=12)
        ax.set_title(f'Channel Std Trends Over Windows - Group: {group_id}', fontsize=14)
        ax.set_yticks([i * offset for i in range(n_channels)])
        ax.set_yticklabels([f'Ch{i}' for i in range(n_channels)])

        plt.tight_layout()
        plt.savefig(kwargs.get('save_path',"./signal_trends_std.png"),dpi=600)

        return fig

    @classmethod
    def plot_electrode_topology_mask(cls,all_ch_check_mask,ch_spacing=1.0, figsize=(6, 8),**kwargs):
        """
        绘制电极拓扑图，根据 all_ch_check_mask 显示通道状态 以及判断 grid_shape
        :param all_ch_check_mask: 通道状态列表，True=好通道(绿色)，False=坏通道(灰色)
        :param group_id: 判断数据来源哪个group
        :param ch_spacing: 电极间距
        :param figsize:图像大小
        :return:
        """

        n_channels = len(all_ch_check_mask)
        if n_channels == 128:
            grid_shape = (16,8)
        else:
            grid_shape = (n_channels,1)
        n_rows, n_cols = grid_shape
        if n_channels != n_rows * n_cols:
            raise ValueError(f"通道数 {n_channels} 与网格 {grid_shape} 不匹配")
        fig, ax = plt.subplots(figsize=figsize)

        # 颜色定义
        color_good = '#4CAF50'  # 绿色
        color_bad = '#9E9E9E'  # 灰色
        edge_color = '#333333'  # 边框颜色

        # 绘制每个电极
        for ch_idx in range(n_channels):
            row = ch_idx // n_cols
            col = ch_idx % n_cols

            x = col * ch_spacing
            y = (n_rows - 1 - row) * ch_spacing

            is_good = all_ch_check_mask[ch_idx]
            face_color = color_good if is_good else color_bad

            # 绘制圆形电极
            circle = Circle((x, y), radius=ch_spacing * 0.35,
                            facecolor=face_color,
                            edgecolor=edge_color,
                            linewidth=1.5)
            ax.add_patch(circle)

            ax.text(x, y, str(ch_idx), ha='center', va='center',
                    fontsize=7, color='white', fontweight='bold')

        # 设置坐标轴
        ax.set_xlim(-0.2, n_cols * ch_spacing + 0.2)
        ax.set_ylim(-0.2, n_rows * ch_spacing + 0.2)
        ax.set_aspect('equal')
        ax.axis('off')

        # 添加标题
        ax.set_title(f'Electrode Topology',fontsize=12)

        plt.tight_layout()
        plt.savefig(kwargs.get('save_path', {"./ElectrodeTopology.png"}), dpi=600)
        return fig
