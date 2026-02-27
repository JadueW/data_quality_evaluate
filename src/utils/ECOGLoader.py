import os.path
import pickle
import warnings

import numpy as np
import mne

from utilities.brpylib import NsxFile, brpylib_ver

from utilities.importrhdutilities import load_file as data_reader


class ECOGloader:
    def __init__(self, path, **kwargs):
        self.path = path
        self.__valid_path__()

        self.kwargs = kwargs

        self.data_prop = {
            "fs": kwargs.get("fs", None),
            "marker": kwargs.get("marker", None),
            "num_ch": kwargs.get("fs", None),
        }
        self.waveform = None

    def __valid_path__(self):
        if not os.path.exists(self.path):
            raise ValueError(f"Path {self.path} does not exist.")

    def __reset_prop__(self):
        self.data_prop.clear()
        self.data_prop = {
            "fs": None,
            "marker": None,
            "num_ch": None,
        }

    def load_data(self, file_name, suffix="rhd"):
        # suffix = os.path.splitext(file_name)[1]
        self.__reset_prop__()
        _fileloc_dir = os.path.join(self.path, file_name)
        if suffix in ['rhd', 'wl']:
            _rs, data_present = data_reader(_fileloc_dir)
            if not data_present:
                raise ValueError(f"{_fileloc_dir} is empty")

            self.waveform = _rs.get("amplifier_data", None)

            if self.waveform is None:
                warnings.warn(f"It does not find the key [amplifier_data] in the file: {_fileloc_dir}")

            # TODO  这种方法不是最合适的方法，但是是目前最快的方法。取另一个端口的数据
            # self.waveform = self.waveform[128:, :]
            self.data_prop["fs"] = _rs['frequency_parameters']['amplifier_sample_rate']

            self.data_prop["marker"] = _rs.get("board_dig_in_data", None)
        elif suffix == 'edf':
            raw = mne.io.read_raw_edf(_fileloc_dir, preload=True, encoding='latin1')
            self.waveform = raw.get_data(return_times=True)[0]
            self.data_prop["fs"] = raw.info['sfreq']
        elif suffix == 'ns':
            # Version control
            brpylib_ver_req = "1.3.1"
            if brpylib_ver.split('.') < brpylib_ver_req.split('.'):
                raise Exception("requires brpylib " + brpylib_ver_req + " or higher, please use latest version")
            # Open file and extract headers
            nsx_file = NsxFile(_fileloc_dir)

            # Extract data - note: data will be returned based on *SORTED* elec_ids, see cont_data['elec_ids']
            # cont_data = nsx_file.getdata(elec_ids, start_time_s, data_time_s, downsample)
            cont_data = nsx_file.getdata("all", 0, "all", 1)

            # Close the nsx file now that all data is out
            nsx_file.close()

            self.data_prop['num_ch'] = len(cont_data['elec_ids']) if isinstance(cont_data['elec_ids'], list) else None
            self.data_prop['fs'] = cont_data['samp_per_s']
            self.waveform = cont_data['data']

        elif suffix == "pkl":
            with open(_fileloc_dir, "rb") as f:
                dataset = pickle.load(f)
                try:
                    self.waveform = dataset['waveform']
                    self.data_prop["fs"] = dataset['fs']
                    self.data_prop["num_ch"] = self.waveform.shape[0]
                except Exception as e:
                    print(e)
                    raise ValueError("")
            _fileloc_dir
            pass

        elif suffix == "mat":
            # TODO
            pass
        else:
            raise ValueError(
                "Can not load other formats of the file,please correct the suffix with 'rhd','mat','edf', 'NSx'")


if __name__ == '__main__':
    path = r"C:\Users\70706\welink\proj\29-实验范式设计\250612深二院术中唤醒\dataset\rawData\5语言"
    filename = 'combine.wl'
    dataloader = ECOGloader(path=path, base_path=path)
    dataloader.load_data(file_name=filename, suffix='wl')
    data = dataloader.waveform
    fs = dataloader.data_prop['fs']
    marker = dataloader.data_prop['marker']
    e_duration = np.argwhere(marker[0, :]).shape[0] / fs
    v_duration = 131.937
    print(e_duration - v_duration)
