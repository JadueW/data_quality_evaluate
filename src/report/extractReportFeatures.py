"""
用来提取相关指标：
    1. 用来绘制 电极拓扑、信号变化趋势图1、信号变化趋势图2
    2. 提供report_data的数据接口
        valid_length
        line_noise
        bad_ch
        total_ch
        bad_ratio
        amp,std,mean的max, min, avg, median, varibility, 1%, 5%, 95% 99%
        impedence_range(min,max,avg)
"""

import numpy as np
from tdigest import TDigest

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
            "valid_length": 0.0,  # 在后续计算中填充
            "line_noise": 0.0,
            "bad_ch": 0,          # 在后续计算中填充
            "total_ch": 0,        # 在后续计算中填充
            "bad_ratio": 0.0,     # 在后续计算中填充
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
            "ch_win_means": [],    # 跨窗口跨通道的均值 [[ch0_win0, ch0_win1, ...], ...]
            "ch_win_stds": [],     # 跨窗口跨通道的标准差 [[ch0_win0, ch0_win1, ...], ...]
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
            n_channels = len(all_win_tdigest)

            n_channels_tdigest = []

            for ch_idx in range(n_channels):
                channel_tdigest = all_win_tdigest[ch_idx]
                merged_tdigest = TDigest()

                # 单通道跨窗口合并
                for win_idx in range(len(channel_tdigest)):
                    merged_tdigest += channel_tdigest[win_idx]

                n_channels_tdigest.append(merged_tdigest)
            all_group_channels_tdigest[group_id] = n_channels_tdigest

        return all_group_channels_tdigest

    def _compute_report_statistics(self):
        all_group_channels_tdigest = self._compute_cross_win()
        all_group_values = {}

        for group_id, channels_tdigest in all_group_channels_tdigest.items():

            group_amp_digest = TDigest()
            for ch_tdigest in channels_tdigest:
                group_amp_digest += ch_tdigest

            all_channel_means = []
            all_channel_stds = []

            for ch_tdigest in channels_tdigest:
                centroids_list = ch_tdigest.centroids_to_list()
                mean_value = self._compute_dgigest_mean(centroids_list)
                all_channel_means.append(mean_value)

                variance_val = sum(
                    c['c'] * (c['m'] - mean_value) ** 2
                    for c in centroids_list
                )

                std_approx = ch_tdigest.percentile(84) - ch_tdigest.percentile(16)
                std_value = np.sqrt(variance_val) if variance_val > 0 else std_approx
                all_channel_stds.append(std_value)

            all_group_values[group_id] = {
                "amp_digest": group_amp_digest,
                "means": np.array(all_channel_means),
                "stds": np.array(all_channel_stds)
            }

        return all_group_values

    def generate_report_statistics(self):
        """
        为每个 group_id 生成独立的统计报告
        :return: 字典 {group_id: report_data}
        """

        all_group_values = self._compute_report_statistics()

        all_group_ch_win_means = self.compute_ch_win_mean()
        all_group_ch_win_stds = self.compute_ch_win_std()

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
            centroids = amp_digest.centroids_to_list()

            amp_mean = self._compute_dgigest_mean(centroids)
            p0 = amp_digest.percentile(0)
            p100 = amp_digest.percentile(100)

            p1 = max(p0, amp_digest.percentile(1))
            p99 = min(p100, amp_digest.percentile(99))

            report_data["amp"].update({
                "min": float(p0),
                "max": float(p100),
                "avg": float(amp_mean),
                "median": float(amp_digest.percentile(50)),
                "variability": float(
                    amp_digest.percentile(84) - amp_digest.percentile(16)
                ),
                "1%": float(p1),
                "5%": float(amp_digest.percentile(5)),
                "95%": float(amp_digest.percentile(95)),
                "99%": float(p99)
            })

            means_array = all_group_ch_win_means.get("group_id",{})

            if len(means_array) > 0:
                report_data["mean"].update({
                    "min": float(np.min(means_array)),
                    "max": float(np.max(means_array)),
                    "avg": float(np.mean(means_array)),
                    "median": float(np.median(means_array)),
                    "variability": float(np.std(means_array)),
                    "1%": float(np.percentile(means_array, 1)),
                    "5%": float(np.percentile(means_array, 5)),
                    "95%": float(np.percentile(means_array, 95)),
                    "99%": float(np.percentile(means_array, 99))
                })

            stds_array = all_group_ch_win_stds.get("group_id",{})

            if len(stds_array) > 0:
                report_data["std"].update({
                    "min": float(np.min(stds_array)),
                    "max": float(np.max(stds_array)),
                    "avg": float(np.mean(stds_array)),
                    "median": float(np.median(stds_array)),
                    "variability": float(np.std(stds_array)),
                    "1%": float(np.percentile(stds_array, 1)),
                    "5%": float(np.percentile(stds_array, 5)),
                    "95%": float(np.percentile(stds_array, 95)),
                    "99%": float(np.percentile(stds_array, 99))
                })

            report_data["ch_win_means"] = \
                all_group_ch_win_means.get(group_id, [])

            report_data["ch_win_stds"] = \
                all_group_ch_win_stds.get(group_id, [])

            all_report_data[group_id] = report_data

        return all_report_data

    def compute_ch_win_mean(self):
        """
        计算输出跨窗口跨通道的均值
        :return: 字典嵌套列表的形式
         all_group_ch_win_means = {
            group_id : [[ch0_0,ch0_1,ch0_2,ch0_3,ch0_4,ch0_5,ch0_6],...],[ch1_0,ch1_1,ch1_2,ch1_3,ch1_4,ch1_5,ch1_6]...],.....]
            # ch0_0代表在win= 0 ,ch = 0的情况下的均值
         }
        """
        all_group_ch_win_means = {}
        for group_id, group_values in self.all_group_statistics_data.items():
            ch_win_means = []
            all_win_tdigest = group_values["all_win_tdigest"]
            all_win_check_mask = group_values["all_win_check_mask"]
            for ch_idx in range(len(all_win_tdigest)):
                channel_tdigest = all_win_tdigest[ch_idx]
                channel_means = []
                for win_idx in range(len(channel_tdigest)):
                    win_status = all_win_check_mask[win_idx]
                    if win_status:
                        centroids_list = channel_tdigest[win_idx].centroids_to_list()
                        mean_value = self._compute_dgigest_mean(centroids_list)
                        channel_means.append(mean_value)
                ch_win_means.append(channel_means)
            all_group_ch_win_means[group_id] = ch_win_means

        return all_group_ch_win_means

    def _compute_dgigest_mean(self, centroids_list) -> float:
        total_weight = 0
        total_value = 0
        for i in range(len(centroids_list)):
            total_weight += centroids_list[i]['c']
            total_value += centroids_list[i]['c'] * centroids_list[i]['m']

        mean_value = total_value / total_weight
        return mean_value

    def compute_ch_win_std(self):
        """
        计算输出跨窗口跨通道的均值
        :return: 字典嵌套列表的形式
        all_group_ch_win_std = {
            group_id : [[ch0_0,ch0_1,ch0_2,ch0_3,ch0_4,ch0_5,ch0_6],...],[ch1_0,ch1_1,ch1_2,ch1_3,ch1_4,ch1_5,ch1_6]...],.....]
            # ch0_0代表在win= 0 ,ch = 0的情况下的std值
        }
        """
        all_group_ch_win_std = {}
        for group_id, group_values in self.all_group_statistics_data.items():
            ch_win_std = []
            all_win_tdigest = group_values["all_win_tdigest"]
            all_win_check_mask = group_values["all_win_check_mask"]

            for ch_idx in range(len(all_win_tdigest)):
                channel_tdigest = all_win_tdigest[ch_idx]
                channel_std = []
                for win_idx in range(len(channel_tdigest)):
                    win_status = all_win_check_mask[win_idx]
                    if win_status:
                        centroids_list = channel_tdigest[win_idx].centroids_to_list()
                        mean_value = self._compute_dgigest_mean(centroids_list)
                        variance_val = 0.0
                        for i in range(len(centroids_list)):
                            variance_val += centroids_list[i]['c'] * (centroids_list[i]['m'] - mean_value) ** 2
                        # 使用P84-P16进行标准差估算，防止Variance为0
                        std_approxy = channel_tdigest[win_idx].percentile(84) - channel_tdigest[win_idx].percentile(16)
                        std_value = np.sqrt(variance_val) if variance_val > 0 else std_approxy
                        channel_std.append(std_value)
                ch_win_std.append(channel_std)
            all_group_ch_win_std[group_id] = ch_win_std

        return all_group_ch_win_std