"""

    聚合统计结果

"""

class StatisticsAggregator:
    def __init__(self, delta=100):
        self.delta = delta
        self.group_ids = []

    def aggregation_all_statistics_data(self, all_statistics):

        all_group_statistics_data = {}

        n_channels = None
        for win_idx in range(len(all_statistics)):
            for group_id in self.group_ids:
                if group_id in all_statistics[win_idx]:
                    n_channels = len(all_statistics[win_idx][group_id]['ch_check_mask'])
                    break
            if n_channels is not None:
                break

        win_length = len(all_statistics)

        for win_idx in range(win_length):
            if win_idx >= len(all_statistics):
                continue

            for group_id in self.group_ids:
                if group_id not in all_statistics[win_idx]:
                    continue

                data = all_statistics[win_idx][group_id]

                if group_id not in all_group_statistics_data:
                    all_group_statistics_data[group_id] = {

                        'all_win_check_mask': [],

                        'all_ch_check_mask': [False] * n_channels,

                        'all_win_tdigest': [[] for _ in range(n_channels)]
                    }

                group_data = all_group_statistics_data[group_id]

                # all_win_check_mask
                group_data['all_win_check_mask'].append(data['win_check_mask'])

                # all_ch_check_mask
                current_ch_mask = group_data['all_ch_check_mask']
                new_ch_mask = data['ch_check_mask']

                for i in range(n_channels):
                    current_ch_mask[i] = current_ch_mask[i] or new_ch_mask[i]

                # all_win_tdigest
                current_tdigests = group_data['all_win_tdigest']
                win_tdigests = data['win_tdigest']

                for ch_idx in range(n_channels):
                    current_tdigests[ch_idx].append(win_tdigests[ch_idx])

        return all_group_statistics_data