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
from statistics import variance

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
        self.timepoints = timepoints
        self.fs = fs
        self.all_group_statistics_data = all_group_statistics_data
        self.impedence_range = impedence

        total_ch, bad_ch, bad_ratio, valid_length,all_ch_check_mask = self._compute_win_ch()
        min_val, max_val, avg_val = self._compute_impedence_range()

        self.all_ch_check_mask = all_ch_check_mask

        # 需要计算的结果
        self.report_data = {
            "valid_length": valid_length,
            "line_noise": 0.0,
            "bad_ch": bad_ch,
            "total_ch": total_ch,
            "bad_ratio": bad_ratio,
            "amp":{
                "min": 0.0,
                "max": 0.0,
                "avg": 0.0,
                "median": 0.0,
                "variability": 0.0,
                "1%": 0.0,
                "5%": 0.0,
                "95%": 0.0,
                "99": 0.0
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
                "99": 0.0
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
                "99": 0.0
            },

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

    def _compute_win_ch(self):
        # 获取电极拓扑的分布情况（不同channel的True，False）
        all_ch_check_mask = self.all_group_statistics_data["all_ch_check_mask"]
        total_ch, bad_ch, bad_ratio = 0, 0, 0.0
        for ch in all_ch_check_mask:
            total_ch += 1
            if not ch:
                bad_ch += 1
            else:
                continue
        bad_ratio = bad_ch / total_ch

        # 获取有效窗口数量
        all_win_check_mask = self.all_group_statistics_data['all_win_check_mask']
        valid_win = 0
        for ch in all_win_check_mask:
            if ch:
                valid_win += 1
        valid_length = valid_win * self.timepoints / self.fs  # 单位：时间 s

        return total_ch, bad_ch, bad_ratio, valid_length,all_ch_check_mask

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
            all_channel_amps = []
            all_channel_stds = []
            all_channel_means = []
            for ch_tdigest in channels_tdigest:
                # 从TDigest计算该通道的特征量
                # 1. 计算amp = max - min
                max_val = ch_tdigest.percentile(100)
                min_val = ch_tdigest.percentile(0)
                amp = max_val - min_val
                all_channel_amps.append(amp)

                # 2. 使用质心 + 权重计算 加权均值
                centroids_list = ch_tdigest.centroids_to_list()
                mean_value = self._compute_dgigest_mean(centroids_list)
                all_channel_means.append(mean_value)

                # 3 使用质心估算标准差
                variance_val = 0.0
                for i in range(len(centroids_list)):
                    variance_val += centroids_list[i]['c'] * (centroids_list[i]['m'] - mean_value)**2
                # 使用P84-P16进行标准差估算，防止Variance为0
                std_approxy = ch_tdigest.percentile(84) - ch_tdigest.percentile(16)
                std_value= np.sqrt(variance_val) if variance_val > 0 else std_approxy
                all_channel_stds.append(std_value)
            all_group_values[group_id] = all_channel_amps, all_channel_means, all_channel_stds

        return all_group_values

    def generate_report_statistics(self):
        all_group_values = self._compute_report_statistics()

        all_amps, all_means, all_stds = [], [], []

        for group_id, (amps, means, stds) in all_group_values.items():
            all_amps.extend(amps)
            all_means.extend(means)
            all_stds.extend(stds)

        # 转换为 numpy 数组
        amps = np.array(all_amps)
        means = np.array(all_means)
        stds = np.array(all_stds)

        for metric_name, values in [("amp", amps), ("mean", means), ("std", stds)]:
            if len(values) == 0:
                continue

            self.report_data[metric_name].update({
                "min": float(np.min(values)),
                "max": float(np.max(values)),
                "avg": float(np.mean(values)),
                "median": float(np.median(values)),
                "variability": float(np.std(values)),
                "1%": float(np.percentile(values, 1)),
                "5%": float(np.percentile(values, 5)),
                "95%": float(np.percentile(values, 95)),
                "99%": float(np.percentile(values, 99))
            })

        return self.report_data

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
            for ch_idx in range(len(all_win_tdigest)):
                channel_tdigest = all_win_tdigest[ch_idx]
                channel_means = []
                for win_idx in range(len(channel_tdigest)):
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
            for ch_idx in range(len(all_win_tdigest)):
                channel_tdigest = all_win_tdigest[ch_idx]
                channel_std = []
                for win_idx in range(len(channel_tdigest)):
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