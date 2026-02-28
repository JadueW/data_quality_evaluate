import os
import psutil


class hardware_resources:
    """
        工具类：用来判断硬件资源
        如：可用内存\可用线程数等
    """
    @classmethod
    def get_hardware_memory(cls):
        """ 内存信息 """
        mem = psutil.virtual_memory()

        # 总内存
        total_gb = round(mem.total / (1024**3), 2)
        # 可用内存（不含缓存）
        available_gb = round(mem.available / (1024**3), 2)
        # 完全空闲内存
        free_gb = round(mem.free / (1024**3), 2)

        # 判断标志位，当前内存是否处于低内存状态
        is_low_mem = mem.available < 2 * (1024**3)    # 可用<2GB视为低内存

        return total_gb, available_gb, free_gb, is_low_mem

    @classmethod
    def get_hardware_cpu(cls):
        """ CPU信息 """
        # 逻辑处理器数量
        logical_cores = psutil.cpu_count(logical=True)

        # 物理处理器数量
        physical_cores = psutil.cpu_count(logical=False)

        # CPU使用率
        cpu_percent = round(psutil.cpu_percent(), 2)

        return logical_cores, physical_cores, cpu_percent


    @classmethod
    def get_hardware_disk(cls):
        """ 磁盘信息 """
        disk = psutil.disk_usage(os.path.abspath("."))
        free_gb = round(disk.free / (1024**3), 2)

        return free_gb

