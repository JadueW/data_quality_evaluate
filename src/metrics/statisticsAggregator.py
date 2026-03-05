# -*- coding:utf-8 -*-
# author:70706
# datetime:2026/3/5
# software: PyCharm
"""
    聚合统计结果

    支持混合统计算法的聚合：
    1. Welford 统计量：用于精确的均值和标准差计算
    2. TDigest 统计量：用于百分位数计算
"""

from .welford_statistics import WelfordArray


class StatisticsAggregator:
    def __init__(self, delta=100):
        self.delta = delta

    def aggregation_all_statistics_data(self, all_statistics):
        """
        聚合所有窗口的统计结果

        支持两种统计算法的聚合：
        - Welford: 用于精确的均值和标准差
        - TDigest: 用于百分位数

        Args:
            all_statistics: 所有窗口的统计数据

        Returns:
            聚合后的统计数据，包含：
            - all_win_check_mask: 窗口质量掩码
            - all_ch_check_mask: 通道质量掩码
            - all_win_welford: Welford 统计量列表
            - all_win_tdigest: TDigest 对象列表
        """
        all_group_statistics_data = {}

        # 首先收集所有组的信息，并找出每个组在每个窗口中的最大通道数
        group_max_channels = {}
        group_ids = set()

        for win_idx in range(len(all_statistics)):
            for group_id in all_statistics[win_idx].keys():
                group_ids.add(group_id)
                # 同时检查 welford 和 tdigest 的通道数（应该一致）
                current_n_channels = len(all_statistics[win_idx][group_id]['win_tdigest'])

                if group_id not in group_max_channels:
                    group_max_channels[group_id] = current_n_channels
                else:
                    group_max_channels[group_id] = max(group_max_channels[group_id], current_n_channels)

        for group_id, max_ch in group_max_channels.items():
            print(f"组 {group_id} 的最大通道数: {max_ch}")

        win_length = len(all_statistics)

        for win_idx in range(win_length):
            for group_id in group_ids:

                data = all_statistics[win_idx][group_id]
                n_channels = group_max_channels[group_id]

                if group_id not in all_group_statistics_data:
                    all_group_statistics_data[group_id] = {
                        'all_win_check_mask': [],
                        'all_ch_check_mask': [False] * n_channels,
                        # Welford 统计量：每个通道保存每个窗口的 WelfordArray
                        'all_win_welford': [[] for _ in range(n_channels)],
                        # TDigest 统计量：每个通道保存每个窗口的 TDigest
                        'all_win_tdigest': [[] for _ in range(n_channels)]
                    }

                group_data = all_group_statistics_data[group_id]

                # 聚合窗口质量掩码
                group_data['all_win_check_mask'].append(data['win_check_mask'])

                # 聚合通道质量掩码（使用 OR 操作）
                current_ch_mask = group_data['all_ch_check_mask']
                new_ch_mask = data['ch_check_mask']

                for i in range(len(new_ch_mask)):
                    current_ch_mask[i] = current_ch_mask[i] or new_ch_mask[i]

                # 聚合 Welford 统计量
                current_welfords = group_data['all_win_welford']
                win_welford = data['win_welford']

                actual_n_channels = win_welford.n_channels
                if actual_n_channels != n_channels:
                    print(f"警告: 窗口 {win_idx}, 组 {group_id} 的 Welford 通道数 {actual_n_channels} 与最大通道数 {n_channels} 不一致")

                # 保存每个窗口的 Welford 统计量（用于后续跨窗口统计）
                for ch_idx in range(min(actual_n_channels, n_channels)):
                    current_welfords[ch_idx].append(win_welford.stats[ch_idx])

                # 聚合 TDigest 统计量
                current_tdigests = group_data['all_win_tdigest']
                win_tdigests = data['win_tdigest']

                actual_n_channels_tdigest = len(win_tdigests)
                if actual_n_channels_tdigest != n_channels:
                    print(f"警告: 窗口 {win_idx}, 组 {group_id} 的 TDigest 通道数 {actual_n_channels_tdigest} 与最大通道数 {n_channels} 不一致")

                for ch_idx in range(min(actual_n_channels_tdigest, n_channels)):
                    current_tdigests[ch_idx].append(win_tdigests[ch_idx])

        return all_group_statistics_data
