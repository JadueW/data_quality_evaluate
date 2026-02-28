# -*- coding:utf-8 -*-
# author:70706
# datetime:2026/2/28 16:34
# software: PyCharm

import numpy as np
import mne


class Preprocessor:
    def __init__(self, raw_data):
        self.raw_data = raw_data
        pass

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
        data = self.raw_data.get("raw_data", None)
        # 拿到映射, 这个映射是电极的物理映射
        mapping = self.raw_data.get("mapping", None)
        assert not mapping, "电极物理映射必须存在"

        total_chs = data.shape[0]
        grouped_data = []
        # 分公司内外两种电极
        if ele_type.lower().startswith("ucortex"):
            assert total_chs > 0 and total_chs % 128 == 0, f"预期数据通道数大于0且为128倍数，得到{total_chs}个通道"

            for i in range(data.shape[0] // 128):
                s = i * 128
                e = s + 128

                # 重映射
                _remapped_data = self.__re_mapping(data[s:e, ...], mapping)

                grouped_data.append(_remapped_data)

        elif ele_type.lower().startswith("pse"):
            # 华科电极暂不支持同时使用多个放大器的情况, 也就是说最多只能有128通道
            assert total_chs == 128, f"接华科电极时，预期数据通道数为128，得到{total_chs}个通道"

            # 如果是华科电极，需要先确定转接器的映射
            connector_mapping = kwargs.get("connector_mapping", None)
            if not connector_mapping:
                connector_mapping = np.arange(128).reshape((12, 8))

            # 先根据转接器调整顺序
            data = self.__re_mapping(data, connector_mapping)

            pse_ch_num = kwargs.get("pse_ch_num", 4)
            pse_num = kwargs.get("pse_num", 1)
            pse_order = kwargs.get("pse_order", "order")

            # 根据电极物理位置，调整映射
            if pse_order == "order":
                pse_order = [[i * pse_ch_num + 1, i * pse_ch_num + pse_ch_num + 1] for i in range(pse_num)]

            pse_order = np.array(pse_order)
            if kwargs.get("index_method"):
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

    def notch_filter(self, data):
        pass

    def pass_filter(self):
        pass

    def bad_check(self):
        pass

    def resample(self):
        pass

    def re_reference(self):
        pass


if __name__ == '__main__':
    print("hi")
