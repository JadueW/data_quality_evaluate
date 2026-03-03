# -*- coding:utf-8 -*-
# author:70706
# datetime:2026/3/3 11:18
# software: PyCharm
import numpy as np

from .metrics.calc_snr import compute_single_window_snr
from .preprocessing.preprocessor import Preprocessor

def handle_statistics(batch_datasets):
    """
    针对统计量指标，进行数据处理
    窗口为5,无重叠
    return:
    {
        group_id:{
        win_check_mask
        ch_check_mask
        processed_data
        }
    }
    """

    # 制作一份数据信息模板
    ds_template = {}
    for k, v in batch_datasets.items():
        if k == "data":
            continue
        ds_template.update({k: v})
    # batch data的预处理模板
    _template = {
        "win_check_mask": [],
        "ch_check_mask": [],
        "processed_data": []
    }

    # 分窗口
    win_size, overlap, wid, s = 5, 0, 0, 0

    grouped_processed_data = {}
    # 对批数据依次分窗处理
    while True:
        e = s + int(win_size * batch_datasets["fs"])
        # 判断退出条件
        if e > batch_datasets["data"].shape[1]:
            break

        # 取窗口
        ds_template.update({"data": batch_datasets["data"][:, s:e]})
        pp = Preprocessor(ds_template)
        _processed_data = pp.start(
            connector_mapping=None,  # 以下参数均为分组时使用的参数，在ele_type为pse-XX时起效
            pse_num=1,
            pse_order="order",
            pse_ch_num="4",
        )
        # 将处理完的窗口数据分组保存
        for k, v in _processed_data.items():
            if k not in grouped_processed_data:
                grouped_processed_data.update({
                    k: _template
                })
            grouped_processed_data[k]["win_check_mask"].append(v["is_good"])
            grouped_processed_data[k]["ch_check_mask"].append(v["ch_check_mask"])
            grouped_processed_data[k]["processed_data"].append(v["processed_data"])

        s = e
        wid += 1

    return grouped_processed_data


def handle_snr(batch_datasets):
    """
    针对snr指标，进行数据处理
    窗口为60s, 重叠30s
    return:
    {
        group_id:{
        win_check_mask
        ch_check_mask
        SNR
        }
    }
    """
    # 制作一份数据信息模板
    ds_template = {}
    for k, v in batch_datasets.items():
        if k == "data":
            continue
        ds_template.update({k: v})
    # batch data的预处理模板
    _template = {
        "win_check_mask": [],
        "ch_check_mask": [],
        "win_SNR": []
    }

    # 分窗口
    win_size, overlap, wid, s = 60, 30, 0, 0

    grouped_snr = {}
    # 对批数据依次分窗处理
    while True:
        e = s + int(win_size * batch_datasets["fs"])
        # 判断退出条件
        if e > batch_datasets["data"].shape[1]:
            break

        # 取窗口
        ds_template.update({"data": batch_datasets["data"][:, s:e]})
        pp = Preprocessor(ds_template)
        _processed_data = pp.start(
            connector_mapping=None,  # 以下参数均为分组时使用的参数，在ele_type为pse-XX时起效
            pse_num=1,
            pse_order="order",
            pse_ch_num="4",
        )
        # 将处理完的窗口数据分组保存
        for k, v in _processed_data.items():
            if k not in grouped_snr:
                grouped_snr.update({
                    k: _template
                })
            is_good = v["is_good"]
            if is_good:
                snr_info = compute_single_window_snr(v["processed_data"], batch_datasets["fs"])
                if not snr_info:
                    grouped_snr[k]["win_SNR"].append(snr_info["snr"])
                else:
                    grouped_snr[k]["win_SNR"].append(np.zeros((-1, pp.group_ch_num)))
            else:
                grouped_snr[k]["win_SNR"].append(np.zeros((-1, pp.group_ch_num)))

            grouped_snr[k]["win_check_mask"].append(is_good)
            grouped_snr[k]["ch_check_mask"].append(v["ch_check_mask"])

        s = s + int(overlap * batch_datasets["fs"])
        wid += 1

    return grouped_snr


if __name__ == '__main__':
    print("hi")
