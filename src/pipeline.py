# -*- coding:utf-8 -*-
# author:70706
# datetime:2026/3/2 14:03
# software: PyCharm

import os.path
from tqdm import tqdm

from src.analyse import handle_statistics, handle_snr, handle_line_noise_detection
from src.data_io.dataParse import DataParse
from src.metrics.statistics import Statistics
from src.metrics.statisticsAggregator import StatisticsAggregator
from src.metrics.calc_snr import SNR_statistics, compute_snr_statistics
from src.report.extractReportFeatures import ExtractReportFeatures
from src.report.report_generator import PDFReportGenerator
from src.visualize.visualizer import Visualizer
from src.preprocessing.preprocessor import Preprocessor


if __name__ == '__main__':

    data_dir = '../data/raw/小黑20260114第二只001对照组'
    output_dir = os.path.join("../results/", data_dir.split('/')[-1])
    os.makedirs(output_dir, exist_ok=True)

    print("========== 数据质量评估开始 ==========")

    data = DataParse(data_dir)
    strategy = data.load_strategy()
    dataloader = data.data_loader(strategy)

    aggregator = StatisticsAggregator(delta=100)

    all_statistics = {}
    win_counter = 0

    timepoints = 0
    fs = 0
    impedence = 0

    is_detect_line_noise = False
    all_line_noise = None

    last_datasets = None
    SNR_data_dict = None


    for datasets in tqdm(dataloader, desc="Processing datasets", mininterval=0.5):

        last_datasets = datasets
        fs = datasets['fs']
        impedence = datasets['impedence']

        preprocessed_data_dict = handle_statistics(datasets)
        timepoints = preprocessed_data_dict[0][0]['processed_data'].shape[1]

        for win_id, win_value in preprocessed_data_dict.items():
            statistics = Statistics(win_value)
            win_group_statistics = statistics.compute_single_win_statistics()

            all_statistics[win_counter] = win_group_statistics
            win_counter += 1

        SNR_data_dict = handle_snr(datasets)

        if not is_detect_line_noise:
            all_line_noise = handle_line_noise_detection(datasets)
            is_detect_line_noise = True

    print("阶段1完成：预处理和统计分析结束")

    print("阶段2：统计聚合")

    all_group_statistics_data = aggregator.aggregation_all_statistics_data(all_statistics)
    all_group_data = SNR_statistics(SNR_data_dict)
    snr_group_statistics = compute_snr_statistics(all_group_data)

    print("阶段2完成：聚合完成")

    print("阶段3：生成 report_data")

    erf = ExtractReportFeatures(all_group_statistics_data, timepoints, fs, impedence)
    all_report_data = erf.generate_report_statistics()

    all_group_ch_win_means = erf.compute_ch_win_mean()
    all_group_ch_win_std = erf.compute_ch_win_std()

    print("阶段3完成：指标计算完成")

    print("阶段4：生成 PDF 报告")

    pdf_generator = PDFReportGenerator(
        output_dir=output_dir,
        pdf_name="data_quality_report.pdf"
    )

    n_groups = len(all_report_data)

    for group_id, report_data in tqdm(
            all_report_data.items(),
            desc="Generating group reports",
            total=n_groups,
            mininterval=0.3
    ):

        total_ch, bad_ch, bad_ratio, valid_length, elec_topo = \
            erf._compute_win_ch(group_id)

        snr_group_statistic = snr_group_statistics[group_id]
        group_line_noise = all_line_noise[group_id]

        total_windows = len(
            all_group_statistics_data[group_id]['all_win_check_mask']
        )
        total_samples = timepoints * total_windows
        total_channels = report_data['total_ch']

        estimated_data_size_bytes = total_samples * total_channels * 8
        data_size_kb = estimated_data_size_bytes / 1024
        data_size_mb = data_size_kb / 1024
        total_duration = total_samples / fs

        bad_channels_list = [
            i for i, is_good in enumerate(elec_topo) if not is_good
        ]

        trend1_image = os.path.join(
            output_dir, f"signal_trends_mean_group{group_id}.png"
        )
        trend2_image = os.path.join(
            output_dir, f"signal_trends_std_group{group_id}.png"
        )

        pdf_results = {
            'valid_length': report_data['valid_length'],
            'bad_ch': report_data['bad_ch'],
            'total_ch': report_data['total_ch'],
            'bad_ratio': report_data['bad_ratio'] * 100,

            'amp': report_data['amp'],
            'std': report_data['std'],
            'snr_range': snr_group_statistic,
            'impedence_range': report_data['impedence_range'],

            'n_channels': total_channels,
            'sample_rate': fs,
            'duration': total_duration,
            'data_kb': data_size_kb,
            'data_mb': data_size_mb,

            'electrode_map_image': os.path.join(
                output_dir, f"elec_mapping_group{group_id}.png"
            ),
            'trend1_image': trend1_image,
            'trend2_image': trend2_image,
            'bad_channels': bad_channels_list,

            'line_noise': group_line_noise['line_noise'],
            'powerline_table': group_line_noise['powerline_table'],

            'notch_freqs': Preprocessor.notch_harmonics
        }

        with tqdm(total=3, desc=f"Group {group_id} plotting",
                  leave=False) as subbar:

            Visualizer.plot_ch_win_mean(
                all_group_ch_win_means,
                group_id=group_id,
                save_path=trend1_image
            )
            subbar.update(1)

            Visualizer.plot_ch_win_std(
                all_group_ch_win_std,
                group_id=group_id,
                save_path=trend2_image
            )
            subbar.update(1)

            Visualizer.plot_electrode_topology_mask(
                elec_topo,
                save_path=os.path.join(
                    output_dir,
                    f"elec_mapping_group{group_id}.png"
                )
            )
            subbar.update(1)

        pdf_generator.add_group(group_id, pdf_results, n_groups=n_groups)

    pdf_generator.finalize()

    print("========== 数据质量评估完成 ==========")