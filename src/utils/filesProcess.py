import os

class FileProcess:
    """
        工具类：
            1. 提供判断文件夹内的文件数的工具函数
            2. 提供判断文件大小的函数
            3. 提供判断硬件资源的函数，包括：CPU、线程、内存资源等
    """

    def __init__(self,file_dir):
        self.file_dir = file_dir


    def count_dir_files(self):
        """
            获取上传文件夹内的 wl/edf/dat 数据文件的文件数量
        :return: l/edf/dat 数据文件的文件数
        """

        files = [f for f in os.listdir(self.file_dir) if f.endswith("wl") or f.endswith("edf") or f.endswith("dat")]
        return len(files)


    def size_single_file(self,raw_file):
        """
            获取单个原始数据文件的字节大小（MB）
        :param raw_file: 原始文件
        :return: MB单位的数据大小
        """

        return os.stat(raw_file).st_size / 1024 / 1024

    def hardware_resources(self):
        pass

