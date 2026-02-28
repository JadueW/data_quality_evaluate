import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Generator, List, Dict, Any, Optional

import numpy as np
import pandas as pd
from datetime import datetime

from src.utils.importrhdutilities import load_file
from src.utils.filesProcess import FileProcess
from src.utils.hardware_resources import hardware_resources

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

        self.mapping = np.array([int(x.strip()) for x in content.replace('\n', ',').split(',') if x.strip()])

        # 缓存文件
        self.files = [os.path.join(self.file_dir, f)for f in os.listdir(self.file_dir) if f.endswith((".wl", ".edf", ".dat"))]

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
            "method": "direct",          # direct / chunked / merged / chunked_merged
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
        if strategy['is_chunked'] and strategy['is_merged']:
            strategy['method'] = "chunked_merged"
        elif strategy['is_chunked']:
            strategy['method'] = "chunked"
        elif strategy['is_merged']:
            strategy['method'] = "merged"
        else:
            strategy['method'] = "direct"

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
        wl_files = [f for f in os.listdir(self.file_dir) if f.endswith(".wl")]
        datasets = {}

        datasets['data'] = data['amplifier_data']
        datasets['impedence'] = self.impedence
        datasets['fs'] = data['frequency_parameters']['amplifier_sample_rate']
        datasets['mapping'] = self.mapping
        datasets['ele_type'] = self.elec_type
        datasets['subject_id'] = wl_files.index(wl_file)

        date_str, time_str = wl_file.split(".")[0].split("_")[1:]
        dt = datetime.strptime(f"{date_str}_{time_str}", "%y%m%d_%H%M%S")
        datasets['date'] = dt.strftime("%Y-%m-%d %H:%M:%S")

        return datasets

    def __parse_edf(self,edf_file):
        # TODO: parse edf file to custom format
        pass

if __name__ == '__main__':
    file_dir = r'D:\dev\data_quality_evaluate\data\raw\对照组wl'
    dp = DataParse(file_dir)

    print(dp.get_count_dir_files)

    strategy = dp.load_strategy()
    print(strategy)
