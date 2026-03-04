"""

    聚合统计结果

"""

class StatisticsAggregator:
    def __init__(self, delta=100):
        self.delta = delta

    def aggregation_all_statistics_data(self, all_statistics):

        all_group_statistics_data = {}

        # 首先收集所有组的信息，并找出每个组在每个窗口中的最大通道数
        group_max_channels = {}
        group_ids = set()

        for win_idx in range(len(all_statistics)):
            for group_id in all_statistics[win_idx].keys():
                group_ids.add(group_id)
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

                        'all_win_tdigest': [[] for _ in range(n_channels)]
                    }

                group_data = all_group_statistics_data[group_id]

                group_data['all_win_check_mask'].append(data['win_check_mask'])

                current_ch_mask = group_data['all_ch_check_mask']
                new_ch_mask = data['ch_check_mask']

                for i in range(len(new_ch_mask)):
                    current_ch_mask[i] = current_ch_mask[i] or new_ch_mask[i]

                # all_win_tdigest - 需要处理通道数不一致的情况
                current_tdigests = group_data['all_win_tdigest']
                win_tdigests = data['win_tdigest']

                actual_n_channels = len(win_tdigests)
                if actual_n_channels != n_channels:
                    print(f"警告: 窗口 {win_idx}, 组 {group_id} 的通道数 {actual_n_channels} 与最大通道数 {n_channels} 不一致")

                for ch_idx in range(actual_n_channels):
                    current_tdigests[ch_idx].append(win_tdigests[ch_idx])

        return all_group_statistics_data
