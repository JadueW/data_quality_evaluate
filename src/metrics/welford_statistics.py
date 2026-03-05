import numpy as np


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

        self.count = 0
        self.mean = 0.0
        self.M2 = 0.0

    def update(self, value):

        self.count += 1
        delta = value - self.mean
        self.mean += delta / self.count
        delta2 = value - self.mean
        self.M2 += delta * delta2

    def batch_update(self, values):

        if not isinstance(values, np.ndarray):
            values = np.array(values, dtype=np.float64)

        n = len(values)
        if n == 0:
            return

        new_mean = np.mean(values)

        new_M2 = np.sum((values - new_mean) ** 2)

        if self.count == 0:
            self.count = n
            self.mean = new_mean
            self.M2 = new_M2
        else:
            total_count = self.count + n
            delta = new_mean - self.mean
            self.M2 += new_M2 + delta ** 2 * self.count * n / total_count
            self.mean = (self.count * self.mean + n * new_mean) / total_count
            self.count = total_count

    def merge(self, other) :

        if other.count == 0:
            return

        if self.count == 0:
            self.count = other.count
            self.mean = other.mean
            self.M2 = other.M2
            return

        total_count = self.count + other.count
        delta = other.mean - self.mean
        self.M2 += other.M2 + delta ** 2 * self.count * other.count / total_count
        self.mean = (self.count * self.mean + other.count * other.mean) / total_count
        self.count = total_count

    @property
    def variance(self) :

        if self.count < 1:
            return 0.0
        return self.M2 / self.count

    @property
    def sample_variance(self) :

        if self.count < 2:
            return 0.0
        return self.M2 / (self.count - 1)

    @property
    def std(self) :

        return np.sqrt(self.variance)

    @property
    def sample_std(self) :

        return np.sqrt(self.sample_variance)

    def get_statistics(self) :

        return {
            'count': self.count,
            'mean': self.mean,
            'variance': self.variance,
            'std': self.std,
            'sample_variance': self.sample_variance,
            'sample_std': self.sample_std
        }

    def __repr__(self) :

        return (f"WelfordStatistics(count={self.count}, "
                f"mean={self.mean:.6f}, std={self.std:.6f})")


class WelfordArray:


    def __init__(self, n_channels):

        self.n_channels = n_channels
        self.stats = [WelfordStatistics() for _ in range(n_channels)]

    def update_channel(self, channel_idx, value) :

        if 0 <= channel_idx < self.n_channels:
            self.stats[channel_idx].update(value)

    def update_channel_batch(self, channel_idx, values) :

        if 0 <= channel_idx < self.n_channels:
            self.stats[channel_idx].batch_update(values)

    def update_all_channels(self, data) :

        n_ch, n_samples = data.shape
        assert n_ch == self.n_channels, f"通道数不匹配: 期望 {self.n_channels}, 得到 {n_ch}"

        for ch_idx in range(n_ch):
            self.stats[ch_idx].batch_update(data[ch_idx, :])

    def get_channel_statistics(self, channel_idx) :

        if 0 <= channel_idx < self.n_channels:
            return self.stats[channel_idx].get_statistics()
        return {}

    def get_all_means(self) :

        return np.array([s.mean for s in self.stats])

    def get_all_stds(self) :

        return np.array([s.std for s in self.stats])

    def get_all_counts(self) :

        return np.array([s.count for s in self.stats])

    def merge(self, other) :

        assert self.n_channels == other.n_channels, "通道数不匹配"
        for i in range(self.n_channels):
            self.stats[i].merge(other.stats[i])

    def __repr__(self) :
        return f"WelfordArray(n_channels={self.n_channels})"


