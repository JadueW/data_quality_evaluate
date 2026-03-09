
import numpy as np
from pytdigest import TDigest

class ExtractReportFeatures:
    def __init__(self,all_group_statistics_data,timepoints,fs,impedence):
        """

        :param all_group_statistics_data:
        :param timepoints: 一个窗口的时间点数
        :param impedence: 阻抗值的列表，ndarray格式
        :param fs: 采样率
        """
        default_timepoints = 10000
        if timepoints == 0:
            timepoints = default_timepoints
        self.timepoints = timepoints
        self.fs = fs
        self.all_group_statistics_data = all_group_statistics_data
        self.impedence_range = impedence


    def _create_report_data_template(self):
        """创建 report_data 的模板结构"""
        min_val, max_val, avg_val = self._compute_impedence_range()

        return {
            "valid_length": 0.0,
            "line_noise": 0.0,
            "bad_ch": 0,
            "total_ch": 0,
            "bad_ratio": 0.0,
            "amp":{
                "min": 0.0,
                "max": 0.0,
                "avg": 0.0,
                "median": 0.0,
                "variability": 0.0,
                "1%": 0.0,
                "5%": 0.0,
                "95%": 0.0,
                "99%": 0.0
            },
            "std":{
                "min": 0.0,
                "max": 0.0,
                "avg": 0.0,
                "median": 0.0,
                "variability": 0.0,
                "1%": 0.0,
                "5%": 0.0,
                "95%": 0.0,
                "99%": 0.0
            },
            "mean":{
                "min": 0.0,
                "max": 0.0,
                "avg": 0.0,
                "median": 0.0,
                "variability": 0.0,
                "1%": 0.0,
                "5%": 0.0,
                "95%": 0.0,
                "99%": 0.0
            },
            "ch_win_means": [],
            "ch_win_stds": [],
            "snr_range":{
                "min": 0.0,
                "max": 0.0,
                "avg": 0.0
            },
            "impedence_range":{
                "min": min_val,
                "max": max_val,
                "avg": avg_val
            }
        }
    def _compute_impedence_range(self):
        impedence_range = self.impedence_range
        min_val = np.min(impedence_range)
        max_val = np.max(impedence_range)
        avg_val = np.mean(impedence_range)
        return min_val, max_val, avg_val

    def _compute_win_ch(self, group_id):
        """
        计算指定 group_id 的通道和窗口统计信息

        :param group_id: 要计算的 group_id
        :return: total_ch, bad_ch, bad_ratio, valid_length, all_ch_check_mask
        """
        group_values = self.all_group_statistics_data[group_id]
        all_ch_check_mask = group_values["all_ch_check_mask"]
        all_win_check_mask = group_values['all_win_check_mask']

        total_ch, bad_ch, bad_ratio = 0, 0, 0.0
        for ch in all_ch_check_mask:
            total_ch += 1
            if not ch:
                bad_ch += 1
            else:
                continue
        bad_ratio = bad_ch / total_ch if total_ch > 0 else 0.0

        # 获取有效窗口数量
        valid_win = sum(1 for is_good in all_win_check_mask if is_good)
        valid_length = valid_win * self.timepoints / self.fs  # 单位：时间 s

        return total_ch, bad_ch, bad_ratio, valid_length, all_ch_check_mask

    def _compute_cross_win(self):
        """
        跨组跨被试合并TDigest，最终输出形状保留了通道层面的TDigest对象
        只合并有效窗口（win_check_mask=True）的TDigest

        all_group_channels_tdigest = {
            group_id_0: []   # n_channels
            group_id_1: []   # n_channels
            ....
        }
        :return:
        """
        all_group_channels_tdigest = {}
        for group_id, group_values in self.all_group_statistics_data.items():
            all_win_tdigest = group_values["all_win_tdigest"]
            all_win_check_mask = group_values["all_win_check_mask"]
            n_channels = len(all_win_tdigest)

            n_channels_tdigest = []

            for ch_idx in range(n_channels):
                channel_tdigest = all_win_tdigest[ch_idx]
                merged_tdigest = TDigest()

                # 单通道跨窗口合并（只合并有效窗口）
                for win_idx in range(len(channel_tdigest)):
                    # 只合并有效窗口的TDigest
                    if win_idx < len(all_win_check_mask) and all_win_check_mask[win_idx]:
                        merged_tdigest += channel_tdigest[win_idx]

                n_channels_tdigest.append(merged_tdigest)
            all_group_channels_tdigest[group_id] = n_channels_tdigest

        return all_group_channels_tdigest

    def _compute_report_statistics(self):
        """
        计算报告所需的统计数据

        优化版本：
        - 使用 Welford 统计量直接获取每个通道的均值和标准差
        - 使用 TDigest 计算幅度的百分位数
        - 只统计有效窗口（win_check_mask=True）的数据
        """
        # 使用绝对导入
        from src.metrics.welford_statistics import WelfordStatistics

        all_group_channels_tdigest = self._compute_cross_win()
        all_group_values = {}

        for group_id, channels_tdigest in all_group_channels_tdigest.items():
            group_values = self.all_group_statistics_data[group_id]
            all_win_welford = group_values["all_win_welford"]
            all_win_check_mask = group_values["all_win_check_mask"]

            # 合并所有通道的 TDigest 用于幅度统计
            group_amp_digest = TDigest(compression=100)
            for ch_tdigest in channels_tdigest:
                group_amp_digest += ch_tdigest

            # 使用 Welford 统计量计算每个通道的均值和标准差
            # 对每个通道的所有窗口统计进行合并（只合并有效窗口）
            all_channel_means = []
            all_channel_stds = []

            for ch_idx in range(len(all_win_welford)):
                channel_welford_stats = all_win_welford[ch_idx]

                # 合并该通道所有窗口的统计（只合并有效窗口）
                merged_welford = WelfordStatistics()
                for win_idx, welford_stat in enumerate(channel_welford_stats):
                    # 只合并有效窗口的Welford统计
                    if (win_idx < len(all_win_check_mask) and
                        all_win_check_mask[win_idx] and
                        welford_stat.count > 0):

                        # 手动合并到新的 WelfordStatistics 对象
                        # 避免直接修改原始统计量
                        n1 = merged_welford.count
                        mean1 = merged_welford.mean
                        m2_1 = merged_welford.M2

                        n2 = welford_stat.count
                        mean2 = welford_stat.mean
                        m2_2 = welford_stat.M2

                        if n1 == 0:
                            merged_welford.count = n2
                            merged_welford.mean = mean2
                            merged_welford.M2 = m2_2
                        else:
                            total = n1 + n2
                            delta = mean2 - mean1
                            merged_welford.M2 = m2_1 + m2_2 + delta ** 2 * n1 * n2 / total
                            merged_welford.mean = (n1 * mean1 + n2 * mean2) / total
                            merged_welford.count = total

                if merged_welford.count > 0:
                    all_channel_means.append(merged_welford.mean)
                    all_channel_stds.append(merged_welford.std)

            all_group_values[group_id] = {
                "amp_digest": group_amp_digest,
                "means": np.array(all_channel_means) if all_channel_means else np.array([]),
                "stds": np.array(all_channel_stds) if all_channel_stds else np.array([])
            }

        return all_group_values

    def generate_report_statistics(self):
        """
        为每个 group_id 生成独立的统计报告

        Returns:
            all_report_data: 字典 {group_id: report_data}
            all_group_ch_win_means: 所有窗口的均值数据，用于绘图
            all_group_ch_win_stds: 所有窗口的标准差数据，用于绘图
        """

        all_group_values = self._compute_report_statistics()

        # 分别获取所有窗口和有效窗口的数据
        all_group_ch_win_means, valid_group_ch_win_means = self.compute_ch_win_mean()
        all_group_ch_win_stds, valid_group_ch_win_stds = self.compute_ch_win_std()

        all_report_data = {}

        for group_id, group_data in all_group_values.items():

            report_data = self._create_report_data_template()

            total_ch, bad_ch, bad_ratio, valid_length, _ = \
                self._compute_win_ch(group_id)

            report_data["valid_length"] = float(valid_length)
            report_data["bad_ch"] = int(bad_ch)
            report_data["total_ch"] = int(total_ch)
            report_data["bad_ratio"] = float(bad_ratio)

            amp_digest = group_data["amp_digest"]

            # 使用 pytdigest 的 .mean 属性直接获取均值
            # 注意：pytdigest 的 inverse_cdf 使用 0-1 范围，而不是 0-100
            amp_mean = amp_digest.mean
            p0 = amp_digest.inverse_cdf(0.0)
            p100 = amp_digest.inverse_cdf(1.0)

            p1 = max(p0, amp_digest.inverse_cdf(0.01))
            p99 = min(p100, amp_digest.inverse_cdf(0.99))

            report_data["amp"].update({
                "min": float(p0),
                "max": float(p100),
                "avg": float(amp_mean),
                "median": float(amp_digest.inverse_cdf(0.5)),
                "variability": float(
                    amp_digest.inverse_cdf(0.84) - amp_digest.inverse_cdf(0.16)
                ),
                "1%": float(p1),
                "5%": float(amp_digest.inverse_cdf(0.05)),
                "95%": float(amp_digest.inverse_cdf(0.95)),
                "99%": float(p99)
            })

            means_array = valid_group_ch_win_means.get(group_id, [])

            if len(means_array) > 0:
                # 将嵌套列表展平为一维数组
                all_means = []
                for ch_means in means_array:
                    all_means.extend(ch_means)
                means_array_flat = np.array(all_means)

                report_data["mean"].update({
                    "min": float(np.min(means_array_flat)),
                    "max": float(np.max(means_array_flat)),
                    "avg": float(np.mean(means_array_flat)),
                    "median": float(np.median(means_array_flat)),
                    "variability": float(np.std(means_array_flat)),
                    "1%": float(np.percentile(means_array_flat, 1)),
                    "5%": float(np.percentile(means_array_flat, 5)),
                    "95%": float(np.percentile(means_array_flat, 95)),
                    "99%": float(np.percentile(means_array_flat, 99))
                })

            stds_array = valid_group_ch_win_stds.get(group_id, [])

            if len(stds_array) > 0:
                # 将嵌套列表展平为一维数组
                all_stds = []
                for ch_stds in stds_array:
                    all_stds.extend(ch_stds)
                stds_array_flat = np.array(all_stds)

                report_data["std"].update({
                    "min": float(np.min(stds_array_flat)),
                    "max": float(np.max(stds_array_flat)),
                    "avg": float(np.mean(stds_array_flat)),
                    "median": float(np.median(stds_array_flat)),
                    "variability": float(np.std(stds_array_flat)),
                    "1%": float(np.percentile(stds_array_flat, 1)),
                    "5%": float(np.percentile(stds_array_flat, 5)),
                    "95%": float(np.percentile(stds_array_flat, 95)),
                    "99%": float(np.percentile(stds_array_flat, 99))
                })


            report_data["ch_win_means"] = \
                all_group_ch_win_means.get(group_id, [])

            report_data["ch_win_stds"] = \
                all_group_ch_win_stds.get(group_id, [])

            all_report_data[group_id] = report_data

        return all_report_data, all_group_ch_win_means, all_group_ch_win_stds

    def compute_ch_win_mean(self):
        """
        计算每个通道每个窗口的均值

        Returns:
            all_group_ch_win_means: 包含所有窗口（包括坏窗口），用于绘图
            valid_group_ch_win_means: 只包含有效窗口的好通道，用于统计分析
        """
        all_group_ch_win_means = {}
        valid_group_ch_win_means = {}

        for group_id, group_values in self.all_group_statistics_data.items():
            all_ch_win_means = []      # 所有窗口
            valid_ch_win_means = []    # 只包含有效窗口的好通道

            all_win_welford = group_values["all_win_welford"]
            all_win_check_mask = group_values["all_win_check_mask"]
            all_win_ch_check_mask = group_values["all_win_ch_check_mask"]  # 每个窗口每个通道的掩码

            for ch_idx in range(len(all_win_welford)):
                channel_welford = all_win_welford[ch_idx]
                all_channel_means = []      # 所有窗口
                valid_channel_means = []    # 只包含有效窗口的好通道

                for win_idx, welford_stat in enumerate(channel_welford):
                    # 对于所有窗口（用于绘图），只要有数据就添加
                    if welford_stat.count > 0:
                        all_channel_means.append(welford_stat.mean)

                    # 对于有效窗口的好通道（用于统计）
                    # 同时检查：窗口是否有效 && 通道是否有效
                    win_status = all_win_check_mask[win_idx]
                    ch_status = all_win_ch_check_mask[win_idx][ch_idx]
                    if win_status and ch_status and welford_stat.count > 0:
                        valid_channel_means.append(welford_stat.mean)

                all_ch_win_means.append(all_channel_means)
                valid_ch_win_means.append(valid_channel_means)

            all_group_ch_win_means[group_id] = all_ch_win_means
            valid_group_ch_win_means[group_id] = valid_ch_win_means

        return all_group_ch_win_means, valid_group_ch_win_means

    def compute_ch_win_std(self):
        """
        计算每个通道每个窗口的标准差

        Returns:
            all_group_ch_win_std: 包含所有窗口（包括坏窗口），用于绘图
            valid_group_ch_win_std: 只包含有效窗口，用于统计分析
        """
        all_group_ch_win_std = {}
        valid_group_ch_win_std = {}

        for group_id, group_values in self.all_group_statistics_data.items():
            all_ch_win_std = []      # 所有窗口
            valid_ch_win_std = []    # 只包含有效窗口

            all_win_welford = group_values["all_win_welford"]
            all_win_check_mask = group_values["all_win_check_mask"]
            all_win_ch_check_mask = group_values["all_win_ch_check_mask"]  # 每个窗口每个通道的掩码

            for ch_idx in range(len(all_win_welford)):
                channel_welford = all_win_welford[ch_idx]
                all_channel_std = []      # 所有窗口
                valid_channel_std = []    # 只包含有效窗口的好通道

                for win_idx, welford_stat in enumerate(channel_welford):
                    # 对于所有窗口（用于绘图），只要有数据就添加
                    if welford_stat.count > 0:
                        all_channel_std.append(welford_stat.std)

                    # 对于有效窗口的好通道（用于统计）
                    # 同时检查：窗口是否有效 && 通道是否有效
                    win_status = all_win_check_mask[win_idx]
                    ch_status = all_win_ch_check_mask[win_idx][ch_idx]
                    if win_status and ch_status and welford_stat.count > 0:
                        valid_channel_std.append(welford_stat.std)

                all_ch_win_std.append(all_channel_std)
                valid_ch_win_std.append(valid_channel_std)

            all_group_ch_win_std[group_id] = all_ch_win_std
            valid_group_ch_win_std[group_id] = valid_ch_win_std

        return all_group_ch_win_std, valid_group_ch_win_std