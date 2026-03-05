# -*- coding:utf-8 -*-
# author:70706
# datetime:2026/3/2 15:03
# software: PyCharm
import signal
from scipy import signal
import numpy as np


def compute_single_window_snr(window_data, sample_rate, activity_threshold_std=3, min_activity_duration=0.1):
    """
    计算单个时间窗口的LFP SNR
    （基于snr_analysis.py的_compute_single_window_snr方法）

    Args:
        window_data: 窗口数据 (n_channels, n_samples)
        sample_rate: 采样率
        activity_threshold_std: 高活动状态检测阈值，
        min_activity_duration: 最小高活动状态持续时间 单位为秒

    Returns:
        dict: 包含SNR和详细信息的字典，或None（如果窗口无效）
    """
    from scipy import ndimage
    n_channels, n_samples = window_data.shape
    # 预处理：去除线性趋势
    detrended_data = signal.detrend(window_data, axis=1)

    # 计算每个通道的包络（使用希尔伯特变换）
    analytic_signal = signal.hilbert(detrended_data, axis=1)
    amplitude_envelope = np.abs(analytic_signal)

    # 平滑包络（100ms窗口）
    smooth_window = int(0.1 * sample_rate)
    if smooth_window % 2 == 0:
        smooth_window += 1

    smoothed_envelope = np.zeros_like(amplitude_envelope)
    for ch in range(n_channels):
        smoothed_envelope[ch, :] = signal.medfilt(amplitude_envelope[ch, :], kernel_size=smooth_window)

    # 一次性构建结构元素
    min_duration_samples = int(min_activity_duration * sample_rate)
    # 形态学核：opening 用一半长度，closing 用全长度
    se_open = np.ones(min_duration_samples // 2, dtype=bool)
    se_close = np.ones(min_duration_samples, dtype=bool)

    # 检测高活动和低活动状态
    # 预分配内存，减少随机访问时间
    high_activity_states = [None] * n_channels
    low_activity_states = [None] * n_channels

    for ch in range(n_channels):
        # TODO 判断当前通道是否为坏道

        ch_envelope = smoothed_envelope[ch, :]

        # 伪影检测
        envelope_mean_initial = np.mean(ch_envelope)
        envelope_std_initial = np.std(ch_envelope)
        artifact_threshold = envelope_mean_initial + activity_threshold_std * envelope_std_initial

        artifact_mask = ch_envelope > artifact_threshold

        # 计算去除伪影后的平均值
        clean_envelope = ch_envelope[~artifact_mask]
        if len(clean_envelope) > 0:
            threshold = np.mean(clean_envelope)
        else:
            threshold = envelope_mean_initial

        # 识别高活动状态
        high_activity_mask = ch_envelope > threshold
        high_activity_mask[artifact_mask] = False

        # 形态学滤波（只做一次 opening + closing）
        high_activity_mask = ndimage.binary_opening(high_activity_mask, structure=se_open)
        high_activity_mask = ndimage.binary_closing(high_activity_mask, structure=se_close)

        # 提取高活动和低活动时段
        ch_high_activity = detrended_data[ch, high_activity_mask]
        ch_low_activity = detrended_data[ch, ~high_activity_mask]

        high_activity_states[ch] = ch_high_activity
        low_activity_states[ch] = ch_low_activity

    # 检查是否有足够的数据
    if (len(np.concatenate(high_activity_states)) == 0 or
            len(np.concatenate(low_activity_states)) == 0):
        return None

    # 计算信号和噪声
    high_activity_pp = np.mean([np.ptp(high_activity) for high_activity in high_activity_states
                                if len(high_activity) > 0])
    low_activity_rms = np.mean([np.sqrt(np.mean(low_activity ** 2)) for low_activity in low_activity_states
                                if len(low_activity) > 0])

    # 计算SNR（分贝）
    if low_activity_rms > 0:
        snr_db = 20 * np.log10(high_activity_pp / low_activity_rms)
    else:
        snr_db = np.nan

    return {
        'snr': snr_db,
        'high_activity_pp': high_activity_pp,
        'low_activity_rms': low_activity_rms,
        'n_high_activity_samples': sum(len(arr) for arr in high_activity_states),
        'n_low_activity_samples': sum(len(arr) for arr in low_activity_states)
    }


def _win_SNR_statistics(snr_data_win_dict):
    group_data = {}
    for group_id, group_value in snr_data_win_dict.items():
        group_data[group_id] = group_value['win_SNR']

    return group_data

def SNR_statistics(snr_data_dict):

    group_ids = list(snr_data_dict[0].keys())
    all_group_data = {}
    for id in group_ids:
        all_group_data[id] = []

    for win_id , win_value in snr_data_dict.items():
        group_data = _win_SNR_statistics(win_value)

        for group_id, group_value in group_data.items():
            all_group_data[group_id].append(group_value)

    return all_group_data


def compute_snr_statistics(all_group_data):

    snr_group_statistics = {}

    for group_id, group_data in all_group_data.items():
        # 合并所有窗口的数据为一个一维数组
        # group_data是list of arrays，需要concatenate
        if not group_data or len(group_data) == 0:
            snr_group_statistics[group_id] = {
                "min": 0.,
                "max": 0.,
                "avg": 0.,
                "median": 0.,
                "variability": 0.,
                "p5-p95": "N/A",
            }
            continue

        all_snr_values = np.concatenate(group_data)

        min_val = np.min(all_snr_values)
        max_val = np.max(all_snr_values)
        avg_val = np.mean(all_snr_values)
        median_val = np.median(all_snr_values)
        std_val = np.std(all_snr_values, ddof=0)

        p5 = np.percentile(all_snr_values, 5)
        p95 = np.percentile(all_snr_values, 95)

        p1 = np.percentile(all_snr_values, 1)
        p99 = np.percentile(all_snr_values, 99)

        snr_statistics = {
            "min": round(min_val, 2),
            "max": round(max_val, 2),
            "avg": round(avg_val, 2),
            "median": round(median_val, 2),
            "variability": round(std_val, 2),
            "p5-p95": f"{p5:.2f} - {p95:.2f}",
            "p1-p99": f"{p1:.2f} - {p99:.2f}"
        }

        snr_group_statistics[group_id] = snr_statistics

    return snr_group_statistics


if __name__ == "__main__":
    all_group_data = {
        0: [
            np.array([20.5, 21.0, 19.8, 22.1]),
            np.array([21.2, 20.8, 20.3, 21.5]),
            np.array([20.1, 21.5, 20.7, 20.9]),
        ],
        1: [
            np.array([20.8, 21.2, 20.5, 21.8]),
            np.array([21.5, 20.9, 21.1, 22.0]),
        ]
    }

    result = compute_snr_statistics(all_group_data)

    # 打印结果
    for group_id, stats in result.items():
        print(f"\nGroup {group_id}:")
        for key, value in stats.items():
            print(f"  {key}: {value}")