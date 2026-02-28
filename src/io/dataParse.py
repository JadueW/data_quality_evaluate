import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Generator, List, Dict, Any, Optional

import numpy as np
import pandas as pd
from datetime import datetime
import mne

from src.utils.importrhdutilities import load_file
from src.utils.filesProcess import FileProcess
from src.utils.hardware_resources import hardware_resources

import math

class DataParse(FileProcess):
    """
        1. 适配多种文件格式的数据加载类，如 .wl/ .edf/ .dat
        2. 判断传入文件夹内的文件总数
        3. 判断每个文件大小
    """
    def __init__(self,file_dir):
        super().__init__(file_dir)

        self.file_dir = file_dir
        self.elec_type = "PSE-4A" if file_dir.__contains__("对照组") else "μCortex0-07"

        # 获取impedence
        files = [f for f in os.listdir(self.file_dir)]
        for idx, file in enumerate(files):
            if file.__contains__("impedence"):
                impedence_file = files[idx]
        imp_data = pd.read_csv(os.path.join(self.file_dir, impedence_file))
        self.impedence = np.array(imp_data['Impedance Magnitude at 1000 Hz (ohms)'])

        # 获取mapping
        for idx, file in enumerate(files):
            if file.__contains__(self.elec_type):
                mpping_file = files[idx]
        with open(os.path.join(self.file_dir, mpping_file), 'r', encoding="utf-8") as f:
            content = f.read()

        self.mapping = np.array([int(x.strip()) for x in content.replace('\n', ',').split(',') if x.strip()])[:3]

        # 缓存文件
        self.files = [os.path.join(self.file_dir, f)for f in os.listdir(self.file_dir) if f.endswith(".wl") or f.endswith( ".edf") or f.endswith(".dat")]

        # 工具类加载
        self.hardware_resources = hardware_resources()

    @property
    def get_count_dir_files(self):
        return self.count_dir_files()

    def get_size_single_file(self,raw_file):
        return self.size_single_file(raw_file)

    def get_profile(self):
        total_gb, available_gb, free_gb, is_low_mem = self.hardware_resources.get_hardware_memory()
        logical_cores, physical_cores, cpu_percent = self.hardware_resources.get_hardware_cpu()
        disk_free_gb = self.hardware_resources.get_hardware_disk()

        return {
            "total_gb": total_gb,
            "available_gb": available_gb,
            "free_gb": free_gb,
            "logical_cores": logical_cores,
            "physical_cores": physical_cores,
            "cpu_percent": cpu_percent,
            "disk_free_gb": disk_free_gb,
            "is_low_mem": is_low_mem
        }

    def load_strategy(self):
        """根据硬件资源和数据文件特征决定加载策略"""
        hardware_status = self.get_profile()

        # 文件信息统计
        single_sizes_gb = [self.get_size_single_file(f) / 1024 for f in self.files]
        max_file_gb = max(single_sizes_gb)
        avg_file_gb = sum(single_sizes_gb) / len(single_sizes_gb)
        total_size_gb = sum(single_sizes_gb)
        file_count = len(self.files)

        # 初始化策略元字典
        strategy = {
            "method": "full",          # full / chunked / merged
            "is_chunked": False,
            "is_parallel": False,
            "is_merged": False,
            "max_workers": 1,
        }

        # 1. 判断是否需要分块 (单文件体积大)
        # 单文件 > 500MB
        CHUNKED_THRESHOLD_GB = 0.5   #  500MB
        if max_file_gb > CHUNKED_THRESHOLD_GB:
            strategy['is_chunked'] = True

        # 2. 判断是否需要合并 (文件多且体积小)
        # 文件数 >= 5 且 单文件 < 100MB
        MERGE_THRESHOLD_COUNT = 5
        MERGE_THRESHOLD_SIZE_GB = 0.1  # 100MB
        if file_count >= MERGE_THRESHOLD_COUNT and avg_file_gb < MERGE_THRESHOLD_SIZE_GB:
            strategy['is_merged'] = True

        # 3. 确定加载方法
        if strategy['is_chunked']:
            strategy['method'] = "chunked"
        elif strategy['is_merged']:
            strategy['method'] = "merged"
        else:
            strategy['method'] = "full"

        # 4. 判断是否并行 (线程数多)
        # CPU核心数 >= 4
        if hardware_status['logical_cores'] >= 4:
            strategy['is_parallel'] = True
            # 并行数不超过 CPU 核心数，也不超过文件数
            strategy['max_workers'] = min(hardware_status['logical_cores'], file_count)

            # 低内存时减少并发数
            if hardware_status['is_low_mem']:
                strategy['max_workers'] = max(1, hardware_status['physical_cores'] // 2)

        # 5. 磁盘空间检查
        if hardware_status['disk_free_gb'] < total_size_gb * 1.5:
            raise ValueError(f"磁盘空间不足: 需要 {total_size_gb * 1.5:.2f}GB, 可用 {hardware_status['disk_free_gb']:.2f}GB")

        return strategy

    def __parse_wl(self,wl_file):
        data, data_present = load_file(os.path.join(self.file_dir,wl_file))
        datasets = {}

        datasets['data'] = data['amplifier_data']
        datasets['impedence'] = self.impedence
        datasets['fs'] = data['frequency_parameters']['amplifier_sample_rate']
        datasets['mapping'] = self.mapping
        datasets['ele_type'] = self.elec_type
        datasets['subject_id'] = self.files.index(wl_file)

        date_str, time_str = wl_file.split(".")[0].split("_")[1:]
        dt = datetime.strptime(f"{date_str}_{time_str}", "%y%m%d_%H%M%S")
        datasets['date'] = dt.strftime("%Y-%m-%d %H:%M:%S")

        return datasets

    def __parse_edf(self,edf_file):
        raw_edf = mne.io.read_raw_edf(os.path.join(self.file_dir,edf_file), preload=True)

        datasets = {}

        datasets['data'] = raw_edf.get_data()
        datasets['impedence'] = self.impedence
        datasets['fs'] = raw_edf.info['sfreq']
        datasets['mapping'] = self.mapping
        datasets['ele_type'] = self.elec_type
        datasets['subject_id'] = self.files.index(edf_file)

        date_str, time_str = edf_file.split(".")[0].split("_")[1:3]
        dt = datetime.strptime(f"{date_str}_{time_str}", "%y%m%d_%H%M%S")
        datasets['date'] = dt.strftime("%Y-%m-%d %H:%M:%S")

        return datasets


    def data_loader(self, strategy=None):
        if strategy is None:
            strategy = self.load_strategy()

        method = strategy['method']
        is_parallel = strategy['is_parallel']
        max_workers = strategy.get('max_workers', 1)

        if method == 'full':
            return self._load_full(is_parallel, max_workers)
        elif method == 'merged':
            return self._load_merged(is_parallel, max_workers)
        elif method == 'chunked':
            return self._load_chunked(is_parallel, max_workers)
        else:
            raise ValueError(f"未知的加载方法: {method}")

    def _load_full(self, is_parallel, max_workers):
        """
        全量加载：针对于数据小，文件少
        策略：一次性加载所有文件，并一起返回
        """
        all_data = []

        # 串行加载所有文件
        if not is_parallel:
            for file_path in self.files:
                all_data.append(self.__parse_wl(os.path.basename(file_path)))
        # 并行加载所有文件
        else:
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = {executor.submit(self.__parse_wl, os.path.basename(f)): f for f in self.files}
                for future in as_completed(futures):
                    try:
                        all_data.append(future.result())
                    except Exception as e:
                        print(f"加载文件失败: {e}")

        yield all_data

    def _load_merged(self, is_parallel, max_workers):
        """
        合并加载:针对于数据小但文件多
        策略：每批加载的数据量不超过空余磁盘容量的1%

        测试结果：针对30MB单个文件，121个文件，不足以占满磁盘容量的1%；此处为了显示迭代器效果所以，选择阈值为磁盘容量额0.001
        """
        hardware = self.get_profile()
        disk_limit_gb = hardware['disk_free_gb'] * 1e-3  # 磁盘容量0.001

        # 计算每个文件大小
        file_sizes_gb = [self.get_size_single_file(f) / 1024 for f in self.files]

        # 分批：每批不超过 disk_limit_gb
        batch_start = 0
        while batch_start < len(self.files):
            batch_size_gb = 0
            batch_end = batch_start

            while batch_end < len(self.files) and batch_size_gb < disk_limit_gb:
                batch_size_gb += file_sizes_gb[batch_end]
                batch_end += 1

            batch_files = self.files[batch_start:batch_end]

            if not is_parallel:
                batch_data = [self.__parse_wl(os.path.basename(f)) for f in batch_files]
            else:
                with ThreadPoolExecutor(max_workers=max_workers) as executor:
                    futures = {executor.submit(self.__parse_wl, os.path.basename(f)): f for f in batch_files}
                    batch_data = []
                    for future in as_completed(futures):
                        try:
                            batch_data.append(future.result())
                        except Exception as e:
                            print(f"加载文件失败: {e}")

            # 返回当前批次的数据
            yield batch_data

            batch_start = batch_end

    def _load_chunked(self, is_parallel, max_workers):
        """
        分块加载：单文件数据大
        策略：阈值为磁盘容量的10%。根据文件大小 / (磁盘容量 * 0.1) 计算分块数
        """
        hardware = self.get_profile()
        threshold_gb = hardware['disk_free_gb'] * 0.1  # 磁盘容量的10%

        file_sizes_gb = [self.get_size_single_file(f) / 1024 for f in self.files]

        for file_idx, file_path in enumerate(self.files):
            file_size_gb = file_sizes_gb[file_idx]

            ratio = file_size_gb / threshold_gb
            num_chunks = math.ceil(ratio)  # 向上取整

            print(f"文件 {os.path.basename(file_path)}: {file_size_gb:.2f}GB, 分成 {num_chunks} 块")

            full_data = self.__parse_wl(os.path.basename(file_path))

            data_array = full_data['data']
            n_channels, n_samples = data_array.shape

            # 计算每块应该有多少个样本
            samples_per_chunk = n_samples // num_chunks

            for chunk_idx in range(num_chunks):
                start_idx = chunk_idx * samples_per_chunk
                if chunk_idx == num_chunks - 1:
                    end_idx = n_samples
                else:
                    end_idx = (chunk_idx + 1) * samples_per_chunk

                chunk_data = full_data.copy()
                chunk_data['data'] = data_array[:, start_idx:end_idx].copy()
                chunk_data['chunk_info'] = {
                    'chunk_idx': chunk_idx,
                    'num_chunks': num_chunks,
                    'start_sample': start_idx,
                    'end_sample': end_idx,
                    'total_samples': n_samples
                }

                yield chunk_data



if __name__ == '__main__':
    file_dir = r'D:\dev\data_quality_evaluate\data\raw\对照组wl'
    dp = DataParse(file_dir)

    print(f"找到 {len(dp.files)} 个数据文件")
    print(f"文件列表: {dp.files}")

    strategy = dp.load_strategy()
    print(f"策略: {strategy}")

    dataloader = dp.data_loader(strategy)
    datasets = next(dataloader)

    print(f"加载的数据量为: {len(datasets)}")

