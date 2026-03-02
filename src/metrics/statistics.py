import numpy as np
from tdigest import TDigest


class Statistics:
    """
    基于tdigest实现概率统计
    """

    def __init__(self, processed_win_data, delta=100):
        """

        :param processed_win_data: 某个窗口的预处理后的数据
        :param delta:tdigest的聚类数量，用于调节概率分布精度
        """
        self.delta = delta
        self.group_data = {}
        self.groups = len(processed_win_data)
        self.group_ids = list(processed_win_data.keys())

        self.processed_win_data = processed_win_data

    def compute_single_win_statistics(self):
        """
        精确计算统计量，输出每个窗口的计算的统计结果
        """
        win_group_statistics = {}

        # 遍历每个group，计算该窗口的统计量
        for group_id, group_data in self.processed_win_data.items():
            n_channels = group_data['processed_data'].shape[0]

            # 定义窗口数据接口
            statistics_win_data = {
                "win_check_mask": group_data['win_check_mask'],
                "ch_check_mask": group_data['ch_check_mask'],
                "win_tdigest": [TDigest(delta=self.delta) for _ in range(n_channels)],
            }

            for ch_idx in range(n_channels):
                ch_data = group_data['processed_data'][ch_idx]
                statistics_win_data['win_tdigest'][ch_idx].batch_update(ch_data)

            win_group_statistics[group_id] = statistics_win_data

        return win_group_statistics


    def aggregation_all_statistics_data(self, all_statistics):

        all_group_statistics_data = {}

        n_channels = None
        for win_idx in range(len(all_statistics)):
            for group_id in self.group_ids:
                if group_id in all_statistics[win_idx]:
                    n_channels = len(all_statistics[win_idx][group_id]['ch_check_mask'])
                    break
            if n_channels is not None:
                break

        win_length = len(all_statistics)

        for win_idx in range(win_length):
            if win_idx >= len(all_statistics):
                continue

            for group_id in self.group_ids:
                if group_id not in all_statistics[win_idx]:
                    continue

                data = all_statistics[win_idx][group_id]

                if group_id not in all_group_statistics_data:
                    all_group_statistics_data[group_id] = {

                        'all_win_check_mask': [],

                        'all_ch_check_mask': [False] * n_channels,

                        'all_win_tdigest': [[] for _ in range(n_channels)]
                    }

                group_data = all_group_statistics_data[group_id]

                # all_win_check_mask
                group_data['all_win_check_mask'].append(data['win_check_mask'])

                # all_ch_check_mask
                current_ch_mask = group_data['all_ch_check_mask']
                new_ch_mask = data['ch_check_mask']

                for i in range(n_channels):
                    current_ch_mask[i] = current_ch_mask[i] or new_ch_mask[i]

                # all_win_tdigest
                current_tdigests = group_data['all_win_tdigest']
                win_tdigests = data['win_tdigest']

                for ch_idx in range(n_channels):
                    current_tdigests[ch_idx].append(win_tdigests[ch_idx])

        return all_group_statistics_data


if __name__ == '__main__':
    print("hi")