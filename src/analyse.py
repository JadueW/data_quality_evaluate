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
    # _template = {
    #     "win_check_mask": [],
    #     "ch_check_mask": [],
    #     "processed_data": []
    # }

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
            pse_ch_num=4,
        )
        grouped_processed_data.update({wid: _processed_data})
        # 将处理完的窗口数据分组保存
        # for k, v in _processed_data.items():
        #     if k not in grouped_processed_data:
        #         grouped_processed_data.update({
        #             k: _template
        #         })
        #     grouped_processed_data[k]["win_check_mask"].append(v["is_good"])
        #     grouped_processed_data[k]["ch_check_mask"].append(v["ch_check_mask"])
        #     grouped_processed_data[k]["processed_data"].append(v["processed_data"])

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
    # _template = {
    #     "win_check_mask": [],
    #     "ch_check_mask": [],
    #     "win_SNR": []
    # }

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
            is_resample=True,  # 计算SNR时降采样, 加快计算时间, 注意后面使用采样频率
            connector_mapping=None,  # 以下参数均为分组时使用的参数，在ele_type为pse-XX时起效
            pse_num=1,
            pse_order="order",
            pse_ch_num=4,
        )

        # 计算每组数据的SNR
        for k, v in _processed_data.items():
            is_good = v["is_good"]

            if is_good:
                snr_info = compute_single_window_snr(v["processed_data"], pp.resample_fs)
                # 并更新snr
                if not np.all(snr_info):
                    v.update({"win_SNR": snr_info["snr"]})
                else:
                    v.update({"win_SNR": np.zeros((pp.group_ch_num,))})
            else:
                v.update({"win_SNR": np.zeros((pp.group_ch_num,))})

            # 去掉预处理数据
            del v["processed_data"]
            grouped_snr.update({wid: {k: v}})
        # 将处理完的窗口数据分组保存
        # for k, v in _processed_data.items():
        #     if k not in grouped_snr:
        #         grouped_snr.update({
        #             k: _template
        #         })
        #     is_good = v["is_good"]
        #     if is_good:
        #         snr_info = compute_single_window_snr(v["processed_data"], batch_datasets["fs"])
        #         if not snr_info:
        #             grouped_snr[k]["win_SNR"].append(snr_info["snr"])
        #         else:
        #             grouped_snr[k]["win_SNR"].append(np.zeros((-1, pp.group_ch_num)))
        #     else:
        #         grouped_snr[k]["win_SNR"].append(np.zeros((-1, pp.group_ch_num)))
        #
        #     grouped_snr[k]["win_check_mask"].append(is_good)
        #     grouped_snr[k]["ch_check_mask"].append(v["ch_check_mask"])

        s = s + int(overlap * pp.resample_fs)
        wid += 1

    return grouped_snr


def handle_line_noise_detection(batch_datasets):
    """
    计算线噪声
    窗口为1s,无overlap,只需要计算一次即可
    return:
    {
        group_id:{
        win_check_mask
        ch_check_mask
        line_noise
        }
    }
    """
    # 制作一份数据信息模板
    ds_template = {}
    for k, v in batch_datasets.items():
        if k == "data":
            continue
        ds_template.update({k: v})

    # 分窗口
    win_size, overlap, wid, s = 1, 0, 0, 0

    grouped_line_noise_flag = {}
    # 对批数据依次分窗处理，最多处理30次，约30s的数据
    while wid < 30:
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
            pse_ch_num=4,
        )

        # 从每组数据中统计
        for k, v in _processed_data.items():
            is_good = v["is_good"]

            if is_good:
                # 如果是好的窗口，从原始数据中计算line noise
                # 取当前组的数据
                line_noise_flag = pp.line_noise_detect(pp.grouped_data[k])
                # 并更新snr
                v.update({"line_noise": line_noise_flag})
                # 去掉预处理数据
                del v["processed_data"]
                grouped_line_noise_flag.update({wid: {k: v}})
            else:
                # 并更新snr
                v.update({"line_noise": np.zeros((pp.group_ch_num, len(pp.harmonics)), dtype=bool)})
                # 去掉预处理数据
                del v["processed_data"]
                grouped_line_noise_flag.update({wid: {k: v}})

        # 修改为更为通道的写法
        s = s + int((win_size - overlap) * pp.fs)
        wid += 1

    """
    将line_noise整理为报告需要的格式
    如果有通道一个line_noise没检测，那么也有可能该通道是坏道
    如果不同窗口，在相同通道下检测的结果不完全一致，对结果影响也不大
    在计算line_noise时，使用的是原始数据。
    """
    _template = {
        "win_check_mask": [],
        "ch_check_mask": [],
        "line_noise": []
    }
    # 重新组织结果
    grouped_ln = {}
    for wid in range(len(grouped_line_noise_flag)):
        wid_line_noise_flag = grouped_line_noise_flag[wid]
        for gid, g_value in wid_line_noise_flag.items():
            if gid not in grouped_ln:
                grouped_ln.update({gid: _template})
            grouped_ln[gid]["win_check_mask"].append(g_value["is_good"])
            grouped_ln[gid]["ch_check_mask"].append(g_value["ch_check_mask"])
            grouped_ln[gid]["line_noise"].append(g_value["line_noise"])

    # 对结果进行统计
    report_line_noise = {}
    for gid, all_win_value in grouped_ln.items():
        if gid not in report_line_noise:
            report_line_noise.update({gid: {"line_noise": [], "powerline_table": []}})

        valid_win = np.argwhere(all_win_value["win_check_mask"])
        gid_ch_line_noise = []
        if valid_win.shape[0]:
            # 存在有效窗口
            valid_win_line_noise = np.array(all_win_value["line_noise"])[valid_win.reshape(-1, ), ...]
            #  (wid, chid, noise_flag) 调整维度
            valid_win_line_noise = np.array(valid_win_line_noise).transpose(1, 0, 2)
            # 取各通道所有窗口结果
            for ch in valid_win_line_noise:
                ch_all_line_noise = valid_win_line_noise[ch, ...]
                win_num, ln_num = ch_all_line_noise.shape
                ratio = np.sum(ch_all_line_noise, axis=1) / win_num
                _temp = np.ones(ln_num, dtype=bool)
                # 在30个窗口中，小于30%支持当前通道有该噪声的则为False
                _temp[ratio < 0.3] = False
                gid_ch_line_noise.append(_temp)

            # 对当前数据做整理，形成报告内容
            gid_ch_line_noise = np.array(gid_ch_line_noise)
            ch_num, ln_num = gid_ch_line_noise.shape
            exit_ln_ch_num = np.sum(gid_ch_line_noise, axis=1)
            for lnid in range(ln_num):
                if exit_ln_ch_num[lnid]:
                    line_noise_name = str((lnid + 1) * 50) + "Hz"
                    exit_ln_ch = np.argwhere(gid_ch_line_noise[:, lnid]).reshape((-1,)) + 1
                    report_line_noise[gid]["line_noise"].append(line_noise_name)
                    report_line_noise[gid]["powerline_table"].append(
                        [line_noise_name, str(exit_ln_ch_num[lnid]), str(exit_ln_ch)]
                    )

    return report_line_noise


if __name__ == '__main__':
    print("hi")
