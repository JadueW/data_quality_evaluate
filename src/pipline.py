# -*- coding:utf-8 -*-
# author:70706
# datetime:2026/3/2 14:03
# software: PyCharm
import os.path

import numpy as np

from src.data_io.dataParse import DataParse
from src.preprocessing.preprocessor import Preprocessor
from src.metrics.statistics import Statistics
from src.metrics.statisticsAggregator import StatisticsAggregator
from src.metrics.calc_snr import compute_single_window_snr


def handle_statistics(batch_datasets):
    """
    针对统计量指标，进行数据处理
    窗口为5,无重叠
    return:
    {
        group_id:{
        win_check_mask
        ch_check_mask
        processed_data
        }
    }
    """

    # 制作一份数据信息模板
    ds_template = {}
    for k, v in batch_datasets.items():
        if k == "data":
            continue
        ds_template.update({k: v})
    # batch data的预处理模板
    _template = {
        "win_check_mask": [],
        "ch_check_mask": [],
        "processed_data": []
    }

    # 分窗口
    win_size, overlap, wid, s = 5, 0, 0, 0

    grouped_processed_data = {}
    # 对批数据依次分窗处理
    while True:
        e = s + int(win_size * batch_datasets["fs"])
        # 判断退出条件
        if e > batch_datasets["data"].shape[1]:
            break

        # 取窗口
        ds_template.update({"data": batch_datasets["data"][:, s:e]})
        pp = Preprocessor(ds_template)
        _processed_data = pp.start(
            connector_mapping=None,  # 以下参数均为分组时使用的参数，在ele_type为pse-XX时起效
            pse_num=1,
            pse_order="order",
            pse_ch_num="4",
        )
        # 将处理完的窗口数据分组保存
        for k, v in _processed_data.items():
            if k not in grouped_processed_data:
                grouped_processed_data.update({
                    k: _template
                })
            grouped_processed_data[k]["win_check_mask"].append(v["is_good"])
            grouped_processed_data[k]["ch_check_mask"].append(v["ch_check_mask"])
            grouped_processed_data[k]["processed_data"].append(v["processed_data"])

        s = e
        wid += 1

    return grouped_processed_data


def handle_snr(batch_datasets):
    """
    针对snr指标，进行数据处理
    窗口为60s, 重叠30s
    return:
    {
        group_id:{
        win_check_mask
        ch_check_mask
        SNR
        }
    }
    """
    # 制作一份数据信息模板
    ds_template = {}
    for k, v in batch_datasets.items():
        if k == "data":
            continue
        ds_template.update({k: v})
    # batch data的预处理模板
    _template = {
        "win_check_mask": [],
        "ch_check_mask": [],
        "win_SNR": []
    }

    # 分窗口
    win_size, overlap, wid, s = 60, 30, 0, 0

    grouped_snr = {}
    # 对批数据依次分窗处理
    while True:
        e = s + int(win_size * batch_datasets["fs"])
        # 判断退出条件
        if e > batch_datasets["data"].shape[1]:
            break

        # 取窗口
        ds_template.update({"data": batch_datasets["data"][:, s:e]})
        pp = Preprocessor(ds_template)
        _processed_data = pp.start(
            connector_mapping=None,  # 以下参数均为分组时使用的参数，在ele_type为pse-XX时起效
            pse_num=1,
            pse_order="order",
            pse_ch_num="4",
        )
        # 将处理完的窗口数据分组保存
        for k, v in _processed_data.items():
            if k not in grouped_snr:
                grouped_snr.update({
                    k: _template
                })
            is_good = v["is_good"]
            if is_good:
                snr_info = compute_single_window_snr(v["processed_data"], batch_datasets["fs"])
                if not snr_info:
                    grouped_snr[k]["win_SNR"].append(snr_info["snr"])
                else:
                    grouped_snr[k]["win_SNR"].append(np.zeros((-1, pp.group_ch_num)))
            else:
                grouped_snr[k]["win_SNR"].append(np.zeros((-1, pp.group_ch_num)))

            grouped_snr[k]["win_check_mask"].append(is_good)
            grouped_snr[k]["ch_check_mask"].append(v["ch_check_mask"])

        s = s + int(overlap * batch_datasets["fs"])
        wid += 1

    return grouped_snr

from src.report.extractReportFeatures import ExtractReportFeatures

if __name__ == '__main__':

    data_dir = '../data/raw/小黑20260114第二只001对照组'
    output_dir = os.path.join("../results/", data_dir.split('/')[-1])

    os.makedirs(output_dir, exist_ok=True)
    data = DataParse(data_dir)
    delta = 100

    # 1. 计算加载策略
    strategy = data.load_strategy()

    # 2. 获取数据迭代器
    dataloader = data.data_loader(strategy)
    print(type(dataloader))

    # 3. 创建聚合器实例
    aggregator = StatisticsAggregator(delta=100)

    # 用于存储所有窗口的统计数据
    all_statistics = {}
    win_counter = 0
    total_windows = 0

    timepoints = 0
    fs = 0
    impedence = 0
    # 4. 迭代处理 预处理和统计分析
    while datasets := next(dataloader):

        timepoints = datasets['data'].shape[1]
        fs = datasets['fs']
        impedence = datasets['impedence']

        # 4.1 针对统计指标展开
        # 4.1.1 获取针对统计分析的预处理数据
        preprocessed_data_dict = handle_statistics(datasets)


        # 4.1.2 对于每个窗口的每个组进行统计
        for win_id, win_value in preprocessed_data_dict.items():
            statistics = Statistics(win_value)

            # 计算单个窗口的statistics
            win_group_statistics = statistics.compute_single_win_statistics()

            # 存储到all_statistics中
            all_statistics[win_counter] = win_group_statistics
            win_counter += 1

        # 4.2 针对SNR展示
        # 4.2.1 获取指数据各窗口下SNR的计算结果
        SNR_data_dict = handle_snr(datasets)
        # TODO 4.2.2 对每个窗口进行统计


    all_group_statistics_data = aggregator.aggregation_all_statistics_data(all_statistics)

    # TODO:5. 计算指定指标，形成report_data数据接口

    erf = ExtractReportFeatures(all_group_statistics_data,timepoints,fs,impedence)

