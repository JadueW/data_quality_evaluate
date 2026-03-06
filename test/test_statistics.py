import numpy as np
import pytest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.metrics.welford_statistics import WelfordStatistics


class TestStatisticsComparison:
    """
        测试类，用来计算测试在不同数据量和不同维度下，
        welford和numpy对于mean和std的计算结果是否相同，保证结果的稳定性和一致性
    """
    test_data_sizes = [100, 1000, 10000, 100000]
    test_ndims = [1, 2, 3, 4]

    @pytest.mark.parametrize("data_size", test_data_sizes)
    @pytest.mark.parametrize("ndim", test_ndims)
    def test_welford_vs_numpy(self, data_size, ndim):

        if ndim == 1:
            data = np.random.randn(data_size) * 10 + 50
        elif ndim == 2:
            data = np.random.randn(data_size // 10, 10) * 10 + 50
        elif ndim == 3:
            data = np.random.randn(data_size // 100, 10, 10) * 10 + 50
        elif ndim == 4:
            n = max(data_size // 1000, 1)
            data = np.random.randn(n, 10, 10, 10) * 10 + 50

        data_flat = data.flatten()

        # Numpy 计算
        numpy_mean = np.mean(data_flat)
        numpy_std = np.std(data_flat, ddof=0)

        # Welford 计算
        welford = WelfordStatistics()
        welford.batch_update(data_flat)

        welford_mean = welford.mean
        welford_std = welford.std

        # 验证 mean 和 std 是否相等
        assert np.isclose(welford_mean, numpy_mean, rtol=1e-10), \
            f"[FAIL] 数据量={data_size}, 维度={ndim}D: Welford mean={welford_mean}, Numpy mean={numpy_mean}"

        assert np.isclose(welford_std, numpy_std, rtol=1e-10), \
            f"[FAIL] 数据量={data_size}, 维度={ndim}D: Welford std={welford_std}, Numpy std={numpy_std}"

        print(f"[PASS] 数据量={data_size:>6}, 维度={ndim}D, 形状={data.shape}: numpy_mean={numpy_mean:.6f}, numpy_std={numpy_std:.6f}, welford_mean={welford_mean:.6f}, welford_std={welford_std:.6f}")


if __name__ == "__main__":
    test = TestStatisticsComparison()

    total_tests = 0
    passed_tests = 0

    for data_size in test.test_data_sizes:
        for ndim in test.test_ndims:
            try:
                test.test_welford_vs_numpy(data_size, ndim)
                passed_tests += 1
            except Exception as e:
                print(f"[SKIP] 数据量={data_size:>6}, 维度={ndim}D: {str(e)[:50]}")
            total_tests += 1
    print(f"passed_tests={passed_tests}, total_tests={total_tests}")
