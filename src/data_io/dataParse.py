import os
from concurrent.futures import ThreadPoolExecutor, as_completed
import re

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
        2. 自动判断文件夹内的数据格式
        3. 判断传入文件夹内的文件总数和单文件大小
        4. 根据硬件资源选择最优加载策略
    """
    def __init__(self, file_dir):
        super().__init__(file_dir)

        self.file_dir = file_dir
        self.elec_type = "PSE" if file_dir.__contains__("对照组") else "uCortex"

        result = self._parse_folder_name()
        self.mapping = result["mapping"]
        self.impedence = result["impedence"]
        self.subject_id = result["subject_id"]
        self.date = result["date"]
        self.impedence_file = result["impedence_file"]

        # 缓存数据文件并自动判断格式
        self.files = [os.path.join(self.file_dir, f) for f in os.listdir(self.file_dir)
                      if f.endswith(".wl") or f.endswith(".edf") or f.endswith(".dat")]
        self.file_format = self._detect_file_format()

        # 工具类加载
        self.hardware_resources = hardware_resources()

    def _parse_folder_name(self):
        """从文件夹名提取日期，subject_id，mapping和impedence"""
        result = {}

        # 提取8位日期
        date_match = re.search(r'(\d{8})', self.file_dir)
        result['date'] = date_match.group(1) if date_match else None

        # 提取subject_id
        subject_match = re.search(r'(第[一二三四五六七八九十百千万]+只\d{3})', self.file_dir)
        result['subject_id'] = subject_match.group(1) if subject_match else None

        # 获取impedence
        files = [f for f in os.listdir(self.file_dir)]
        impedence_file = None
        for idx, file in enumerate(files):
            if file.__contains__("impedence"):
                impedence_file = files[idx]
                break
        if impedence_file is None:
            raise FileNotFoundError(f"未找到阻抗文件: 文件名需包含'impedence'")
        imp_data = pd.read_csv(os.path.join(self.file_dir, impedence_file))
        if imp_data.__contains__("Impedance Magnitude at 1000 Hz (ohms)"):
            result['impedence'] = np.array(imp_data['Impedance Magnitude at 1000 Hz (ohms)'])
        else:
            result['impedence'] = np.array(imp_data['Magnitude'])
        result['impedence_file'] = imp_data

        # 获取mapping
        mapping_file = None
        for idx, file in enumerate(files):
            if file.__contains__(self.elec_type):
                mapping_file = files[idx]
                break
        if mapping_file is None:
            raise FileNotFoundError(f"未找到映射文件: 文件名需包含'{self.elec_type}'")

        mapping_path = os.path.join(self.file_dir, mapping_file)
        try:
            # 方法1：使用 pandas 读取，自动处理空值
            mapping_df = pd.read_csv(mapping_path, header=None)
            mapping_df = mapping_df.dropna(axis=1, how='all')
            result['mapping'] = mapping_df.values.astype(int)
        except Exception as e:
            try:
                result['mapping'] = np.genfromtxt(mapping_path, dtype=int, delimiter=',', invalid_raise=False)
                if result['mapping'].ndim == 1 and len(result['mapping']) == 128:
                    result['mapping'] = result['mapping'].reshape((16, 8))
            except Exception as e2:
                raise ValueError(f"无法读取映射文件 {mapping_file}: {e}, {e2}")

        return result

    def _detect_file_format(self):
        """
        自动检测文件夹内的数据文件格式
        """
        if not self.files:
            raise ValueError("文件夹内没有找到 .wl / .edf / .dat 格式的数据文件")

        format_count = {"wl": 0, "edf": 0, "dat": 0}
        for f in self.files:
            if f.endswith(".wl"):
                format_count["wl"] += 1
            elif f.endswith(".edf"):
                format_count["edf"] += 1
            elif f.endswith(".dat"):
                format_count["dat"] += 1
        max_format = max(format_count, key=format_count.get)
        if format_count[max_format] == 0:
            raise ValueError("无法确定文件格式")

        print(f"检测到数据格式: {max_format.upper()}, 文件数量: {format_count[max_format]}")
        return max_format

    @property
    def get_count_dir_files(self):
        return self.count_dir_files()

    def get_size_single_file(self, raw_file):
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

    def _parse_file(self, file_path):
        """
        统一文件解析接口，根据文件格式自动选择解析方法
        返回标准 raw_data接口字典
        """
        file_ext = os.path.splitext(file_path)[1].lower()

        if file_ext == '.wl':
            return self.__parse_wl(file_path)
        elif file_ext == '.edf':
            return self.__parse_edf(file_path)
        elif file_ext == '.dat':
            return self.__parse_dat(file_path)
        else:
            raise ValueError(f"不支持的文件格式: {file_ext}")

    def check_data(self,data,ch_idx):
        """
        针对非标数据,需要每次手动修改
        :param data:
        :param ch_idx: 单个通道或者通道列表
        :return:
        """
        check_data = data['amplifier_data']
        n_channels =check_data.shape[0]

        if n_channels == 128:
            for ch in ch_idx:
                ch_interval = check_data[ch+1] * 1000
                check_data[ch] = ch_interval
            return check_data
        else:
            invalid_data = np.zeros((128, check_data.shape[1]))
            count = 0
            for ch in range(n_channels):
                if ch in ch_idx:
                    continue
                else:
                    invalid_data[count,:] = check_data[ch]
                count += 1

            for ch in ch_idx:
                ch_interval = check_data[ch+1] * 1000
                invalid_data[ch] = ch_interval

            return invalid_data

    def check_data2(self,data):
        """针对大白的数据修复"""
        channels = 128
        check_data = data
        n_channels = check_data.shape[0]
        repaired_data = np.zeros((128, check_data.shape[1]))
        if n_channels > 128:
            for ch in range(channels):
                repaired_data[ch,:] = check_data[ch,:] * 10e6
        else:
            for ch in range(n_channels):
                repaired_data[ch,:] = check_data[ch,:] * 10e6
            for ch in range(n_channels,channels):
                repaired_data[ch,:] = np.random.randint(low=-6000,high=6000,size=check_data.shape[1])

        return repaired_data

    def __parse_wl(self, wl_file):
        """解析 .对照组wl 格式文件"""
        data, data_present = load_file(wl_file)
        # repaired_data = self.check_data2(data)
        datasets = {}

        datasets['data'] = data['amplifier_data']
        datasets['impedence'] = self.impedence / 1000.0
        datasets['fs'] = data['frequency_parameters']['amplifier_sample_rate']
        datasets['mapping'] = self.mapping
        datasets['ele_type'] = self.elec_type
        datasets['subject_id'] = self.subject_id
        datasets['date'] = self.date
        datasets['impedence_file'] = self.impedence_file

        return datasets

    def __parse_edf(self, edf_file):
        """解析 .edf 格式文件"""
        raw_edf = mne.io.read_raw_edf(edf_file, preload=True, verbose=False)
        data = raw_edf.get_data()
        repaired_data = self.check_data2(data)

        datasets = {}
        datasets['data'] = repaired_data
        datasets['impedence'] = self.impedence
        datasets['fs'] = raw_edf.info['sfreq']
        datasets['mapping'] = self.mapping
        datasets['ele_type'] = self.elec_type
        datasets['subject_id'] = self.subject_id
        datasets['date'] = self.date
        datasets['impedence_file'] = self.impedence_file

        return datasets

    def __parse_dat(self, dat_file):
        #TODO: 解析 .dat待实现
        pass


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
        策略：一次性加载所有文件，合并所有data，其他字段保持不变
        """
        all_data = []

        if not is_parallel:
            for file_path in self.files:
                all_data.append(self._parse_file(file_path))
        else:
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                all_data = list(executor.map(self._parse_file, self.files))

        merged_dataset = {}
        all_datas = [d['data'] for d in all_data]
        merged_dataset['data'] = np.concatenate(all_datas, axis=1)

        for key in all_data[0].keys():
            if key != 'data':
                merged_dataset[key] = all_data[0][key]



        yield merged_dataset

    def _load_merged(self, is_parallel, max_workers):
        """
        合并加载:针对于数据小但文件多
        策略：每批加载的数据量不超过空余磁盘容量的1%，合并每批的data字段
        """
        hardware = self.get_profile()
        disk_limit_gb = hardware['disk_free_gb'] * 1e-3  # 磁盘容量0.001

        file_sizes_gb = [self.get_size_single_file(f) / 1024 for f in self.files]

        batch_start = 0
        while batch_start < len(self.files):
            batch_size_gb = 0
            batch_end = batch_start

            while batch_end < len(self.files) and batch_size_gb < disk_limit_gb:
                batch_size_gb += file_sizes_gb[batch_end]
                batch_end += 1

            batch_files = self.files[batch_start:batch_end]

            # 加载当前批次
            if not is_parallel:
                batch_data_list = [self._parse_file(f) for f in batch_files]
            else:
                with ThreadPoolExecutor(max_workers=max_workers) as executor:
                    batch_data_list = list(executor.map(self._parse_file, batch_files))

            merged_batch = {}
            target_key = 'amplifier_data'

            arrays_to_merge = [np.atleast_2d(d['data'][target_key]) for d in batch_data_list]
            merged_batch['data'] = np.concatenate(arrays_to_merge, axis=1)
            for key in batch_data_list[0].keys():
                if key != 'data':
                    merged_batch[key] = batch_data_list[0][key]

            print(f"Batch loaded: {len(batch_data_list)} files merged. Shape: {merged_batch['data'].shape}")
            yield merged_batch

            batch_start = batch_end

    def _load_chunked(self, is_parallel, max_workers):
        hardware = self.get_profile()
        safe_threshold_gb = hardware['available_gb'] * 0.2

        for file_path in self.files:
            file_size_gb = self.get_size_single_file(file_path) / 1024
            num_chunks = max(1, math.ceil(file_size_gb / safe_threshold_gb))

            print(f"--- 正在处理: {os.path.basename(file_path)} ---")
            print(f"大小: {file_size_gb:.2f}GB, 内存安全阈值: {safe_threshold_gb:.2f}GB, 分块数: {num_chunks}")

            if file_path.endswith('.edf'):
                raw_edf = mne.io.read_raw_edf(file_path, preload=False, verbose=False)  # 不预加载
                n_samples = raw_edf.n_times
                samples_per_chunk = n_samples // num_chunks

                for chunk_idx in range(num_chunks):
                    start_idx = chunk_idx * samples_per_chunk
                    end_idx = n_samples if chunk_idx == num_chunks - 1 else (chunk_idx + 1) * samples_per_chunk

                    data_slice, _ = raw_edf[:, start_idx:end_idx]
                    repaired_data = self.check_data2(data_slice)

                    yield self._wrap_dataset(repaired_data, chunk_idx, num_chunks, start_idx, end_idx, n_samples)

                del raw_edf  #

            else:
                full_data = self._parse_file(file_path)
                data_array = full_data['data']
                n_channels, n_samples = data_array.shape
                samples_per_chunk = n_samples // num_chunks

                for chunk_idx in range(num_chunks):
                    start_idx = chunk_idx * samples_per_chunk
                    end_idx = n_samples if chunk_idx == num_chunks - 1 else (chunk_idx + 1) * samples_per_chunk

                    chunk_data_content = data_array[:, start_idx:end_idx].copy()

                    chunk_package = full_data.copy()
                    chunk_package['data'] = chunk_data_content
                    chunk_package['chunk_info'] = {
                        'chunk_idx': chunk_idx,
                        'num_chunks': num_chunks,
                        'start_sample': start_idx,
                        'end_sample': end_idx,
                        'total_samples': n_samples
                    }
                    yield chunk_package

                del full_data
                del data_array

    def _wrap_dataset(self, data, c_idx, n_chunks, start, end, total):
        """辅助方法：统一包装输出格式"""
        return {
            'data': data,
            'impedence': self.impedence,
            'fs': 2000,
            'mapping': self.mapping,
            'ele_type': self.elec_type,
            'subject_id': self.subject_id,
            'date': self.date,
            'impedence_file': self.impedence_file,
            'chunk_info': {
                'chunk_idx': c_idx,
                'num_chunks': n_chunks,
                'start_sample': start,
                'end_sample': end,
                'total_samples': total
            }
        }


if __name__ == '__main__':
    # 测试 WL 格式
    file_dir = r'D:\code\data_quality_evaluate\data\raw\对照组edf'
    dp = DataParse(file_dir)

    print(f"找到 {len(dp.files)} 个数据文件")
    print(f"文件格式: {dp.file_format}")
    print(f"电极类型: {dp.elec_type}")

    strategy = dp.load_strategy()
    print(f"策略: {strategy}")

    dataloader = dp.data_loader(strategy)
    datasets = next(dataloader)

    print(f"加载的数据量为: {len(datasets)}, 数据类型为:{type(datasets)}")

    print(datasets[0].keys())
