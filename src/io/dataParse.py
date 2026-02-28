import os

import numpy as np
import pandas as pd
from datetime import datetime

from src.utils.importrhdutilities import load_file
from src.utils.filesProcess import FileProcess
from src.utils.hardware_resources import hardware_resources


class data_parse(FileProcess):
    """
        1. 适配多种文件格式的数据加载类，如 .wl/ .edf/ .dat
        2. 判断传入文件夹内的文件总数
        3. 判断每个文件大小
    """
    def __init__(self,file_dir):
        super(FileProcess).__init__(file_dir=file_dir)

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

        # 工具类加载
        self.hardware_resources = hardware_resources()

    @property
    def get_count_dir_files(self):
        return self.get_count_dir_files()

    def get_size_single_file(self,raw_file):
        return self.size_single_file(raw_file)


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