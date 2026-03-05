# -*- coding:utf-8 -*-
# author:70706
# datetime:2026/3/5
# software: PyCharm
"""
Welford 在线统计算法实现

用于高效计算均值、方差和标准差，具有以下优点：
1. 数值稳定性好，避免灾难性抵消
2. 单次遍历数据
3. 支持在线更新和合并
4. 内存效率高，只需维护少量状态变量

参考文献：
Welford, B. P. (1962). "Note on a method for calculating corrected sums of squares and products".
Technometrics. 4 (3): 419–420.
"""


import numpy as np
from typing import Union, List, Optional


class WelfordStatistics:
    """
    Welford 在线统计算法实现

    用于计算单个数据流的均值、方差和标准差

    Attributes:
        count: 样本数量
        mean: 当前均值
        M2: 平方和之和 (用于计算方差)
    """

    __slots__ = ['count', 'mean', 'M2']

    def __init__(self):
        """
        初始化 Welford 统计量
        """
        self.count = 0
        self.mean = 0.0
        self.M2 = 0.0

    def update(self, value: float) -> None:
        """
        使用单个值更新统计量

        Args:
            value: 新的数据值
        """
        self.count += 1
        delta = value - self.mean
        self.mean += delta / self.count
        delta2 = value - self.mean
        self.M2 += delta * delta2

    def batch_update(self, values: Union[np.ndarray, List[float]]) -> None:
        """
        使用批量值更新统计量

        Args:
            values: 数据数组或列表
        """
        # 转换为 numpy 数组以提高性能
        if not isinstance(values, np.ndarray):
            values = np.array(values, dtype=np.float64)

        # 批量更新算法
        n = len(values)
        if n == 0:
            return

        # 计算新数据的均值
        new_mean = np.mean(values)

        # 计算新数据的平方和
        new_M2 = np.sum((values - new_mean) ** 2)

        # 合并到当前统计量
        if self.count == 0:
            self.count = n
            self.mean = new_mean
            self.M2 = new_M2
        else:
            # 使用并行算法合并统计量
            total_count = self.count + n
            delta = new_mean - self.mean
            self.M2 += new_M2 + delta ** 2 * self.count * n / total_count
            self.mean = (self.count * self.mean + n * new_mean) / total_count
            self.count = total_count

    def merge(self, other: 'WelfordStatistics') -> None:
        """
        合并另一个 Welford 统计量到当前统计量

        使用并行算法合并两个统计量，适用于：
        - 多线程/多进程统计聚合
        - 分布式统计计算
        - 跨窗口统计合并

        Args:
            other: 另一个 WelfordStatistics 实例
        """
        if other.count == 0:
            return

        if self.count == 0:
            self.count = other.count
            self.mean = other.mean
            self.M2 = other.M2
            return

        # 并行算法合并
        total_count = self.count + other.count
        delta = other.mean - self.mean
        self.M2 += other.M2 + delta ** 2 * self.count * other.count / total_count
        self.mean = (self.count * self.mean + other.count * other.mean) / total_count
        self.count = total_count

    @property
    def variance(self) -> float:
        """
        计算总体方差 (population variance)

        Returns:
            总体方差
        """
        if self.count < 1:
            return 0.0
        return self.M2 / self.count

    @property
    def sample_variance(self) -> float:
        """
        计算样本方差 (sample variance)

        使用 n-1 作为分母（无偏估计）

        Returns:
            样本方差
        """
        if self.count < 2:
            return 0.0
        return self.M2 / (self.count - 1)

    @property
    def std(self) -> float:
        """
        计算总体标准差 (population standard deviation)

        Returns:
            总体标准差
        """
        return np.sqrt(self.variance)

    @property
    def sample_std(self) -> float:
        """
        计算样本标准差 (sample standard deviation)

        使用 n-1 作为分母（无偏估计）

        Returns:
            样本标准差
        """
        return np.sqrt(self.sample_variance)

    def get_statistics(self) -> dict:
        """
        获取所有统计量

        Returns:
            包含 count, mean, variance, std 的字典
        """
        return {
            'count': self.count,
            'mean': self.mean,
            'variance': self.variance,
            'std': self.std,
            'sample_variance': self.sample_variance,
            'sample_std': self.sample_std
        }

    def __repr__(self) -> str:
        """
        字符串表示
        """
        return (f"WelfordStatistics(count={self.count}, "
                f"mean={self.mean:.6f}, std={self.std:.6f})")


class WelfordArray:
    """
    Welford 统计数组，用于管理多个数据流的统计

    适用于多通道数据的统计，例如脑电数据的多个电极通道

    Attributes:
        n_channels: 通道数量
        stats: WelfordStatistics 对象列表
    """

    def __init__(self, n_channels: int):
        """
        初始化 Welford 统计数组

        Args:
            n_channels: 通道数量
        """
        self.n_channels = n_channels
        self.stats = [WelfordStatistics() for _ in range(n_channels)]

    def update_channel(self, channel_idx: int, value: float) -> None:
        """
        更新单个通道的统计量

        Args:
            channel_idx: 通道索引
            value: 数据值
        """
        if 0 <= channel_idx < self.n_channels:
            self.stats[channel_idx].update(value)

    def update_channel_batch(self, channel_idx: int, values: Union[np.ndarray, List[float]]) -> None:
        """
        批量更新单个通道的统计量

        Args:
            channel_idx: 通道索引
            values: 数据数组
        """
        if 0 <= channel_idx < self.n_channels:
            self.stats[channel_idx].batch_update(values)

    def update_all_channels(self, data: np.ndarray) -> None:
        """
        批量更新所有通道的统计量

        Args:
            data: 形状为 (n_channels, n_samples) 的数据
        """
        n_ch, n_samples = data.shape
        assert n_ch == self.n_channels, f"通道数不匹配: 期望 {self.n_channels}, 得到 {n_ch}"

        for ch_idx in range(n_ch):
            self.stats[ch_idx].batch_update(data[ch_idx, :])

    def get_channel_statistics(self, channel_idx: int) -> dict:
        """
        获取单个通道的统计量

        Args:
            channel_idx: 通道索引

        Returns:
            统计量字典
        """
        if 0 <= channel_idx < self.n_channels:
            return self.stats[channel_idx].get_statistics()
        return {}

    def get_all_means(self) -> np.ndarray:
        """
        获取所有通道的均值

        Returns:
            形状为 (n_channels,) 的均值数组
        """
        return np.array([s.mean for s in self.stats])

    def get_all_stds(self) -> np.ndarray:
        """
        获取所有通道的标准差

        Returns:
            形状为 (n_channels,) 的标准差数组
        """
        return np.array([s.std for s in self.stats])

    def get_all_counts(self) -> np.ndarray:
        """
        获取所有通道的样本数量

        Returns:
            形状为 (n_channels,) 的样本数量数组
        """
        return np.array([s.count for s in self.stats])

    def merge(self, other: 'WelfordArray') -> None:
        """
        合并另一个 WelfordArray 到当前数组

        Args:
            other: 另一个 WelfordArray 实例
        """
        assert self.n_channels == other.n_channels, "通道数不匹配"
        for i in range(self.n_channels):
            self.stats[i].merge(other.stats[i])

    def __repr__(self) -> str:
        """
        字符串表示
        """
        return f"WelfordArray(n_channels={self.n_channels})"


if __name__ == '__main__':
    # 测试 WelfordStatistics
    print("测试 WelfordStatistics:")
    data = [1.0, 2.0, 3.0, 4.0, 5.0]

    ws = WelfordStatistics()
    for val in data:
        ws.update(val)

    print(f"单值更新: {ws.get_statistics()}")

    # 批量更新
    ws_batch = WelfordStatistics()
    ws_batch.batch_update(data)
    print(f"批量更新: {ws_batch.get_statistics()}")

    # numpy 验证
    np_mean = np.mean(data)
    np_std = np.std(data)
    print(f"NumPy: mean={np_mean:.6f}, std={np_std:.6f}")

    # 测试合并
    ws1 = WelfordStatistics()
    ws1.batch_update([1.0, 2.0, 3.0])

    ws2 = WelfordStatistics()
    ws2.batch_update([4.0, 5.0])

    ws1.merge(ws2)
    print(f"合并后: {ws1.get_statistics()}")

    # 测试 WelfordArray
    print("\n测试 WelfordArray:")
    data_2d = np.array([
        [1.0, 2.0, 3.0, 4.0, 5.0],
        [2.0, 4.0, 6.0, 8.0, 10.0],
        [1.5, 2.5, 3.5, 4.5, 5.5]
    ])

    wa = WelfordArray(n_channels=3)
    wa.update_all_channels(data_2d)

    print(f"所有通道均值: {wa.get_all_means()}")
    print(f"所有通道标准差: {wa.get_all_stds()}")

    # numpy 验证
    np_means = np.mean(data_2d, axis=1)
    np_stds = np.std(data_2d, axis=1)
    print(f"NumPy 均值: {np_means}")
    print(f"NumPy 标准差: {np_stds}")
