from tdigest import TDigest
from .welford_statistics import WelfordArray


class Statistics:
    """
    混合统计算法实现：
    1. Welford 在线统计算法：用于计算精确的均值、标准差（数值稳定、内存高效）
    2. TDigest 概率统计算法：用于计算百分位数（适合大规模数据）

    两种算法互补使用，提供完整的统计分析能力
    """

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
        """
        精确计算统计量，输出每个窗口的计算的统计结果

        使用混合算法：
        - Welford: 计算均值、标准差（精确且数值稳定）
        - TDigest: 计算百分位数（内存高效）
        """
        win_group_statistics = {}

        # 遍历每个group，计算该窗口的统计量
        for group_id, group_data in self.processed_win_data.items():
            n_channels = group_data['processed_data'].shape[0]
            processed_data = group_data['processed_data']

            # 定义窗口数据接口
            statistics_win_data = {
                "win_check_mask": group_data['is_good'],
                "ch_check_mask": group_data['ch_check_mask'],
                # Welford 统计：用于精确计算均值和标准差
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