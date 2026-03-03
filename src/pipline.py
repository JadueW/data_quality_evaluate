# -*- coding:utf-8 -*-
# author:70706
# datetime:2026/3/2 14:03
# software: PyCharm
import os.path

from src.analyse import handle_statistics, handle_snr
from src.data_io.dataParse import DataParse
from src.metrics.statistics import Statistics
from src.metrics.statisticsAggregator import StatisticsAggregator

from src.report.extractReportFeatures import ExtractReportFeatures

from src.visualize.visualizer import Visualizer

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

    # 5. 计算指定指标，形成report_data数据接口
    erf = ExtractReportFeatures(all_group_statistics_data,timepoints,fs,impedence)
    report_data = erf.generate_report_statistics()  # 数据字典，参考ExtractReportFeatures中init方法

    # 5.1 生成绘图所需要的数据
    elec_topo = erf.all_ch_check_mask
    all_group_ch_win_means = erf.compute_ch_win_mean()
    all_group_ch_win_std = erf.compute_ch_win_std()

    # 5.2 生成图像，默认保存在当前目录下,save_path参数可配置
    # Visualizer当作工具类使用，所以全部都是类方法
    visualize_output = "../results"
    Visualizer.plot_ch_win_mean(all_group_ch_win_means,save_path=os.path.join(visualize_output,"ch_win_mean.png"))
    Visualizer.plot_ch_win_std(all_group_ch_win_std,save_path=os.path.join(visualize_output,"ch_win_std.png"))
    Visualizer.plot_electrode_topology_mask(elec_topo,save_path=os.path.join(visualize_output,"electrode_topology_mask.png"))


    # TODO: 6. 报告生成


