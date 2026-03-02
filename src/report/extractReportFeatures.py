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

class ExtractReportFeatures:
    def __init__(self,all_group_statistics_data):
        self.all_group_statistics_data = all_group_statistics_data

        # 获取电极拓扑的分布情况（不同channel的True，False）
        self.all_ch_check_mask = self.all_group_statistics_data["all_ch_check_mask"]

        # 需要计算的结果
        self.report_data = {
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

