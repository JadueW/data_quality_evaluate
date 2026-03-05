from tdigest import TDigest
from .welford_statistics import WelfordArray


class Statistics:


    def __init__(self, processed_win_data, delta=100):
        """

        :param processed_win_data: 某个窗口的预处理后的数据
        :param delta: tdigest的聚类数量，用于调节概率分布精度
        """
        self.delta = delta
        self.group_data = {}
        self.groups = len(processed_win_data)
        self.group_ids = list(processed_win_data.keys())

        self.processed_win_data = processed_win_data

    def compute_single_win_statistics(self):

        win_group_statistics = {}

        # 遍历每个group，计算该窗口的统计量
        for group_id, group_data in self.processed_win_data.items():
            n_channels = group_data['processed_data'].shape[0]
            processed_data = group_data['processed_data']

            # 定义窗口数据接口
            statistics_win_data = {
                "win_check_mask": group_data['is_good'],
                "ch_check_mask": group_data['ch_check_mask'],
                # Welford 统计：用于计算均值和标准差
                "win_welford": WelfordArray(n_channels=n_channels),
                # TDigest 统计：用于计算百分位数
                "win_tdigest": [TDigest(delta=self.delta) for _ in range(n_channels)],
            }

            # 同时更新两种统计量
            for ch_idx in range(n_channels):
                ch_data = processed_data[ch_idx]

                # 更新 Welford 统计
                statistics_win_data['win_welford'].update_channel_batch(ch_idx, ch_data)

                # 更新 TDigest 统计
                statistics_win_data['win_tdigest'][ch_idx].batch_update(ch_data)

            win_group_statistics[group_id] = statistics_win_data

        return win_group_statistics



if __name__ == '__main__':
    print("hi")