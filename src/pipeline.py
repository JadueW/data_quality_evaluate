# -*- coding:utf-8 -*-
# author:70706
# datetime:2026/3/2 14:03
# software: PyCharm
import os.path

from src.analyse import handle_statistics, handle_snr, handle_line_noise_detection
from src.data_io.dataParse import DataParse
from src.metrics.statistics import Statistics
from src.metrics.statisticsAggregator import StatisticsAggregator
from src.metrics.calc_snr import SNR_statistics,compute_snr_statistics

from src.report.extractReportFeatures import ExtractReportFeatures
from src.report.report_generator import PDFReportGenerator

from src.visualize.visualizer import Visualizer

from src.preprocessing.preprocessor import Preprocessor

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

    # line_noise_detect 记录
    is_detect_line_noise = False
    all_line_noise = None

    # 存储数据集用于后续使用
    last_datasets = None
    SNR_data_dict = None

    # 计算valid_length
    time_points = 0

    # 4. 迭代处理 预处理和统计分析
    try:
        while datasets := next(dataloader):
            last_datasets = datasets
            ds_timepoints = datasets['data'].shape[1]
            fs = datasets['fs']
            impedence = datasets['impedence']
            mapping = datasets['mapping']

            # 4.1 针对统计指标展开
            # 4.1.1 获取针对统计分析的预处理数据
            preprocessed_data_dict = handle_statistics(datasets)
            time_points = preprocessed_data_dict[0][0]['processed_data'].shape[1]

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

            # 4.3 计算line_noise
            if not is_detect_line_noise:
                all_line_noise = handle_line_noise_detection(datasets)
                is_detect_line_noise = True

    except StopIteration as e:
        print("数据质量评估【预处理和统计分析】完成")

    all_group_statistics_data = aggregator.aggregation_all_statistics_data(all_statistics)
    all_group_data = SNR_statistics(SNR_data_dict)
    snr_group_statistics = compute_snr_statistics(all_group_data)

    # 5. 计算指定指标，形成report_data数据接口
    erf = ExtractReportFeatures(all_group_statistics_data, timepoints, fs, impedence)
    all_report_data = erf.generate_report_statistics()  # 数据字典，参考ExtractReportFeatures中init方法
    print("数据质量评估【指标计算】完成")


    # 5.1 生成绘图所需要的数据
    all_group_ch_win_means = erf.compute_ch_win_mean()
    all_group_ch_win_std = erf.compute_ch_win_std()
    print("数据质量评估【生成绘图所需数据】完成")

    # 6. 创建 PDF 报告生成器实例（所有组共用同一个 PDF）
    pdf_generator = PDFReportGenerator(
        output_dir=output_dir,
        pdf_name="data_quality_report.pdf"
    )

    # 根据report_data的group_id来决定生成几个report
    n_groups = len(all_report_data)
    for group_id, report_data in all_report_data.items():

        # 6. 报告生成
        # 6.1 准备报告数据字典
        # 获取当前group的通道和窗口统计信息
        total_ch, bad_ch, bad_ratio, valid_length, elec_topo = erf._compute_win_ch(group_id)
        snr_group_statistic = snr_group_statistics[group_id]
        group_line_noise = all_line_noise[group_id]

        # 计算当前group的数据大小
        total_windows = len(all_group_statistics_data[group_id]['all_win_check_mask'])
        total_samples = timepoints * total_windows
        total_channels = report_data['total_ch']

        estimated_data_size_bytes = total_samples * total_channels * 8
        data_size_kb = estimated_data_size_bytes / 1024
        data_size_mb = data_size_kb / 1024

        total_duration = total_samples / fs

        bad_channels_list = [i for i, is_good in enumerate(elec_topo) if not is_good]

        valid_length_sec = report_data['valid_length']

        trend1_image = os.path.join(output_dir, f"signal_trends_mean_group{group_id}.png")
        trend2_image = os.path.join(output_dir, f"signal_trends_std_group{group_id}.png")

        pdf_results = {
            # 基础统计（数值格式化在 report_generator 中处理）
            'valid_length': valid_length_sec,
            'bad_ch': report_data['bad_ch'],
            'total_ch': report_data['total_ch'],
            'bad_ratio': report_data['bad_ratio'] * 100,

            # 统计数据（嵌套结构，保持原始数值）
            'amp': report_data['amp'],
            'std': report_data['std'],
            'snr_range': snr_group_statistic,
            'impedence_range': report_data['impedence_range'],

            # 数据采集信息
            'n_channels': total_channels,
            'sample_rate': fs,
            'duration': total_duration,
            'data_kb': data_size_kb,
            'data_mb': data_size_mb,

            # 图片路径和坏通道列表
            'electrode_map_image': os.path.join(output_dir, f"elec_mapping_group{group_id}.png"),
            'trend1_image': trend1_image,
            'trend2_image': trend2_image,
            'bad_channels': bad_channels_list,

            # 线噪声数据
            'line_noise': group_line_noise['line_noise'],
            'powerline_table': group_line_noise['powerline_table'],

            # 陷波频率
            'notch_freqs': Preprocessor.notch_harmonics
        }

        # 6.2 生成当前group的趋势图
        print(f"正在生成 Group {group_id} 的趋势图 和 电极拓扑图...")
        Visualizer.plot_ch_win_mean(
            all_group_ch_win_means,
            group_id=group_id,
            save_path=os.path.join(output_dir, f"signal_trends_mean_group{group_id}.png")
        )
        Visualizer.plot_ch_win_std(
            all_group_ch_win_std,
            group_id=group_id,
            save_path=os.path.join(output_dir, f"signal_trends_std_group{group_id}.png")
        )

        # 6.3 生成电极拓扑图
        Visualizer.plot_electrode_topology_mask(
            elec_topo,
            save_path=os.path.join(output_dir, f"elec_mapping_group{group_id}.png")
        )

        # 6.4 将当前 group 内容追加到报告
        pdf_generator.add_group(group_id, pdf_results, n_groups=n_groups)
        print(f"Group {group_id} 内容已追加到报告")

    # 6.5 所有 group 追加完毕，生成最终 PDF
    pdf_generator.finalize()
