# -*- coding:utf-8 -*-
# author:70706
# datetime:2026/3/2 14:03
# software: PyCharm
import os.path

from src.data_io.dataParse import DataParse
from src.preprocessing.preprocessor import Preprocessor
from src.metrics.statistics import Statistics
from src.metrics.statisticsAggregator import StatisticsAggregator


if __name__ == '__main__':

    data_dir = '../data/raw/小黑20260114第二只001对照组'
    output_dir = os.path.join("../results/",data_dir.split('/')[-1])

    os.makedirs(output_dir,exist_ok=True)
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

    # 4. 迭代处理 预处理和统计分析
    while datasets := next(dataloader):

        # 4.1 获取数据后进行预处理
        ds = Preprocessor(datasets)

        # TODO: 完成预处理后续模块
        preprocessed_data_dict = {}

        # 4.2 对于每个窗口的每个组进行统计
        for win_id, win_value in preprocessed_data_dict.items():
            statistics = Statistics(win_value)

            # 计算单个窗口的statistics
            win_group_statistics = statistics.compute_single_win_statistics()

            # 存储到all_statistics中
            all_statistics[win_counter] = win_group_statistics
            win_counter += 1

    all_group_statistics_data = aggregator.aggregation_all_statistics_data(all_statistics)

    # TODO:5. 计算指定指标，形成report_data数据接口


