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
    def __init__(self,all_group_statistics_data,timepoints,fs):
        """

        :param all_group_statistics_data:
        :param timepoints: 一个窗口的时间点数
        :param fs: 采样率
        """
        self.timepoints = timepoints
        self.fs = fs
        self.all_group_statistics_data = all_group_statistics_data

        total_ch, bad_ch, bad_ratio, valid_length = self._compute_win_ch()

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
                "min": 0.0,
                "max": 0.0,
                "avg": 0.0
            }
        }

    def _compute_win_ch(self):
        # 获取电极拓扑的分布情况（不同channel的True，False）
        self.all_ch_check_mask = self.all_group_statistics_data["all_ch_check_mask"]
        total_ch, bad_ch, bad_ratio = 0, 0, 0.0
        for ch in self.all_ch_check_mask:
            total_ch += 1
            if not ch:
                bad_ch += 1
            else:
                continue
        bad_ratio = bad_ch / total_ch

        # 获取有效窗口数量
        self.all_win_check_mask = self.all_group_statistics_data['all_win_check_mask']
        valid_win = 0
        for ch in self.all_win_check_mask:
            if ch:
                valid_win += 1
        valid_length = valid_win * self.timepoints / self.fs  # 单位：时间 s

        return total_ch, bad_ch, bad_ratio, valid_length

    def _compute_amp_statistics(self):
        all_win_tdigest = self.all_group_statistics_data["all_win_tdigest"]