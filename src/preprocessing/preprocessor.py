# -*- coding:utf-8 -*-
# author:70706
# datetime:2026/2/28 16:34
# software: PyCharm

import numpy as np
from scipy.signal import iirnotch, filtfilt
from mne.filter import filter_data


class Preprocessor:
    def __init__(self, raw_data):
        self.raw_data = raw_data
        self.group_ch_num = None
        self.fs = self.raw_data.get("fs", None)
        if not self.fs:
            raise AssertionError("未获取到采样频率fs")
        self.harmonics = [50, 100, 150, 200]
        self.ch_check_mask = None

    def group(self, **kwargs):
        """
        将数据分为多个神经界面（电极）的数据，每个神经界面视为一级数据
        可能包含uCortex0-X 型号电极
        也可能包含华科精准PSE-XX 型号电极
        但是均使用we-linking放大器

        uCortex0电极，设置转为一个放大器连接一个电极即128通道
        其他公司电极，设置默认使用转接器连接放大器，手动设置分组，一个放大器可连接多个电极

        connector_mapping:None,连接华科电极时, 使用不同的转接器，会有不同的映射，默认使用八爪鱼映射顺序映射
        pse_num: int, 连接的华科电极数量，默认为1
        pse_ch_num: int, 连接华科电极时，其每个电极通道总数，默认为4
        pse_order: str OR List[list], 连接华科电极时，其通道总数，默认为"order" 表示顺序映射,
                    如果为List[list], 则就包含每个电极的连接范围，如[[1,4], [7,10]], 左闭右开
        index_method: int, psd_order为List[list],使用0索引还是1索引, 默认为1

        return:
            grouped_data: np.ndarray
        """
        ele_type = self.raw_data.get("ele_type", "")
        data = self.raw_data.get("data", None)
        # 拿到映射, 这个映射是电极的物理映射
        mapping = self.raw_data.get("mapping", None)
        assert not np.all(mapping), "电极物理映射必须存在"

        total_chs = data.shape[0]
        grouped_data = []
        # 分公司内外两种电极
        if ele_type.lower().startswith("ucortex"):
            self.group_ch_num = 128
            assert total_chs > 0 and total_chs % self.group_ch_num == 0, f"预期数据通道数大于0且为128倍数，得到{total_chs}个通道"

            for i in range(data.shape[0] // self.group_ch_num):
                s = i * self.group_ch_num
                e = s + self.group_ch_num

                # 重映射
                _remapped_data = self.__re_mapping(data[s:e, ...], mapping)

                grouped_data.append(_remapped_data)

        elif ele_type.lower().startswith("pse"):
            # 华科电极暂不支持同时使用多个放大器的情况, 也就是说最多只能有128通道
            assert total_chs == 128, f"接华科电极时，预期数据通道数为128，得到{total_chs}个通道"

            # 如果是华科电极，需要先确定转接器的映射
            connector_mapping = kwargs.get("connector_mapping", None)
            if not connector_mapping:
                connector_mapping = np.arange(128).reshape((16, 8))

            # 先根据转接器调整顺序
            data = self.__re_mapping(data, connector_mapping)

            pse_ch_num = kwargs.get("pse_ch_num", 4)
            pse_num = kwargs.get("pse_num", 1)
            pse_order = kwargs.get("pse_order", "order")
            self.group_ch_num = pse_ch_num

            # 根据电极物理位置，调整映射
            if pse_order == "order":
                pse_order = [[i * pse_ch_num + 1, i * pse_ch_num + pse_ch_num + 1] for i in range(pse_num)]

            pse_order = np.array(pse_order)
            if kwargs.get("index_method", 1):
                pse_order = pse_order - 1

            # 再依次选取各组数据
            for i_rng in pse_order:
                s, e = i_rng[0], i_rng[1]
                _remapped_data = self.__re_mapping(data[s:e, :], mapping)
                grouped_data.append(_remapped_data)

        else:
            raise AssertionError(f"目前只接受两种电极类型, 分别为pse和uCortex, 得到了一个{ele_type}类型")

        return grouped_data

    def __re_mapping(self, data, new_mapping):
        """
        数据的重映射
        """
        new_mapping = np.reshape(new_mapping, (-1,))
        data = data[new_mapping, ...]
        return data

    def line_noise_detect(self, data):
        """
        检测线噪声，频率分辨率为1Hz
        :param data: 输入数据，形状为 (n_channels, n_samples)
        :return: noise_flag: 布尔数组，形状为 (n_channels,)，True表示该通道存在工频噪声异常
        """
        # ========== 1. 校验输入和分辨率（确保频率分辨率为1Hz） ==========
        n_channels, n_samples = data.shape
        # 频率分辨率Δf = fs / n_samples，要求Δf=1Hz → n_samples必须等于fs
        if self.fs != n_samples:
            raise ValueError(f"为保证1Hz频率分辨率，数据长度需等于采样率（当前采样率{self.fs}，数据长度{n_samples}）")

        # ========== 2. 计算FFT和幅值谱（仅保留正频率） ==========
        # 沿时长维度（-1维）计算FFT
        fft_rs = np.fft.fft(data, axis=-1, norm=None)
        # 计算幅值谱（归一化：非直流分量×2/N，直流分量/N）
        fft_amp = np.abs(fft_rs) / n_samples
        fft_amp[:, 1:] = fft_amp[:, 1:] * 2  # 正频率部分幅值还原

        # 生成频率轴（仅保留正频率）
        freqs = np.fft.fftfreq(n_samples, 1 / self.fs)
        positive_mask = freqs >= 0
        freqs_pos = freqs[positive_mask]
        fft_amp_pos = fft_amp[:, positive_mask]

        # ========== 3. 定位工频及其谐波的频率索引 ==========
        # 找到50/100/150Hz对应的索引（分辨率1Hz，直接匹配）
        freq_indices = []
        for freq in self.harmonics:
            if freq in freqs_pos:
                freq_indices.append(np.where(freqs_pos == freq)[0][0])
            else:
                raise ValueError(f"频率{freq}Hz超出奈奎斯特频率（{self.fs / 2}Hz），请检查采样率")

        # ========== 4. 峰值检测+异常判断 ==========
        # 策略：计算工频谐波幅值与周围频率幅值的比值，超过阈值则判定为异常
        noise_flag = np.zeros((n_channels, len(self.harmonics)), dtype=bool)
        threshold = 3.0  # 幅值比值阈值（可根据实际场景调整）

        for ch in range(n_channels):
            # 提取当前通道的幅值谱
            ch_amp = fft_amp_pos[ch]

            # 计算每个工频谐波的局部幅值均值（周围±5Hz，排除自身）
            harmonic_amps = []
            for idx in freq_indices:
                # 取周围频率的幅值（避免越界）
                start = max(0, idx - 5)
                end = min(len(ch_amp) - 1, idx + 5)
                local_amps = ch_amp[start:end + 1]
                local_mean = np.mean(local_amps[local_amps != ch_amp[idx]])  # 排除自身
                # 计算当前谐波幅值与局部均值的比值
                amp_ratio = ch_amp[idx] / local_mean if local_mean > 0 else np.inf
                harmonic_amps.append(amp_ratio)

            # 谐波的比值超过阈值，判定为存在异常工频噪声
            for hid, ratio in enumerate(harmonic_amps):
                if ratio > threshold:
                    noise_flag[ch, hid] = True

        return noise_flag

    def notch_filter(self, data):
        '''
        此处方法与静息态分析代码中的方法一致，参数不可调
        from mne.filter import notch_filter
        data = data * 1.0
        fs = config['fs']
        f0_list = config['notch_freqs_list']
        notch_width = config['notch_width']
        notch_method = config['notch_method']
        notched_data = data
        for f in f0_list:
           notched_data = notch_filter(notched_data, fs, f, notch_widths=notch_width, method=notch_method)
        return notched_data
        '''

        data = data * 1.0

        Q = 30
        notch_freqs = self.harmonics

        for freq in notch_freqs:
            b, a = iirnotch(freq, Q=Q, fs=self.fs)
            data = filtfilt(b, a, data, axis=-1)
        return data

    def pass_filter(self, data):
        """
        此处方法与静息态分析代码中的方法一致, 参数不可调
        """
        l_freq = 1
        h_freq = 200
        l_trans_bandwidth = 1
        h_trans_bandwidth = 10
        method = "iir"

        filtered_data = filter_data(data, sfreq=self.fs, l_freq=l_freq, h_freq=h_freq,
                                    l_trans_bandwidth=l_trans_bandwidth, h_trans_bandwidth=h_trans_bandwidth,
                                    method=method)

        return filtered_data

    def bad_check(self, data):
        """
        此处方法与静息态分析代码中的方法一致, 参数不可调
        return:
            is_win_good: bool 当前窗口是否为坏窗
            ch_check_mask: List[bool] 当前窗口所有的通道的检查结果
        """
        total_ch_num = data.shape[0]
        self.ch_check_mask = np.array([True for _ in range(total_ch_num)])

        std_signal = np.std(data, axis=-1, ddof=1)
        bad_channel_mask = std_signal > 100
        if np.sum(bad_channel_mask) / total_ch_num > 0.3:
            is_win_good = False
            self.ch_check_mask = ~self.ch_check_mask
        else:
            self.ch_check_mask[std_signal > 100] = False
            is_win_good = True
        return is_win_good, self.ch_check_mask

    def resample(self):

        pass

    def re_reference(self, data):
        """
        此处方法与静息态分析代码中的方法一致, 参数不可调
        使用的坏道去除后的所有通道平均
        """
        cared_data = data[self.ch_check_mask, ...]
        mean_signal = np.mean(cared_data, axis=0)
        return cared_data - mean_signal

    def start(self, **kwargs):
        rs = {}
        grouped_data = self.group(**kwargs)
        for gid in range(len(grouped_data)):
            gid_data = grouped_data[gid]
            gid_data = self.notch_filter(gid_data)
            gid_data = self.pass_filter(gid_data)
            is_good, ch_mask = self.bad_check(gid_data)
            if is_good:
                gid_data = self.re_reference(gid_data)

            rs.update({
                gid: {
                    "is_good": is_good,
                    "ch_check_mask": ch_mask,
                    "processed_data": gid_data,
                }
            })
        return rs


if __name__ == '__main__':
    uCortex_fake_data = {
        "data": np.random.randn(256, 10000),
        "fs": 2000,
        "mapping": np.arange(128).reshape((16, 8)),
        "ele_type": "uCortex0-7",
        "subject_id": "",
        "date": "",

    }
    pse_fake_data = {
        "data": np.random.randn(128, 10000),
        "fs": 2000,
        "mapping": np.arange(4).reshape((1, -1)),
        "ele_type": "PSE-4A",
        "subject_id": "",
        "date": "",

    }
    pp = Preprocessor(pse_fake_data)
    pp.group(pse_num=2, pse_order="order")
    print("hi")
