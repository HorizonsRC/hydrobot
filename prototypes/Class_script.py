"""Script to run through a processing task with the processor class."""
import matplotlib as plt
from annalist.annalist import Annalist

from hydrobot.processor import Processor

processing_parameters = {
    "base_url": "http://hilltopdev.horizons.govt.nz/",
    "standard_hts_filename": "RawLogger.hts",
    "check_hts_filename": "boo.hts",
    "site": "Whanganui at Te Rewa",
    "from_date": "2021-06-01 00:00",
    "to_date": "2023-11-30 8:30",
    "frequency": "5T",
    "standard_measurement": "Water level statistics: Point Sample",
    "check_measurement": "External S.G. [Water Level NRT]",
    "defaults": {
        "high_clip": 20000,
        "low_clip": 0,
        "delta": 1000,
        "span": 10,
        "gap_limit": 12,
    },
}

ann = Annalist()
stream_format_str = (
    "%(asctime)s, %(analyst_name)s, %(function_name)s, %(site)s, "
    "%(measurement)s, %(from_date)s, %(to_date)s, %(message)s"
)
ann.configure(
    logfile="output_dump/bot_annals.csv",
    analyst_name="Annie the analyst!",
    file_format_str=stream_format_str,
)

data = Processor(
    processing_parameters["base_url"],
    processing_parameters["site"],
    processing_parameters["standard_hts_filename"],
    processing_parameters["standard_measurement"],
    processing_parameters["frequency"],
    processing_parameters["from_date"],
    processing_parameters["to_date"],
    processing_parameters["check_hts_filename"],
    processing_parameters["check_measurement"],
    processing_parameters["defaults"],
)

data.import_data()

data.clip()
data.remove_spikes()

data.delete_range("2021-06-29 11:00", "2021-06-30 11:25")
data.insert_missing_nans()

data.gap_closer()
data.quality_encoder()

data.data_exporter("output_dump/")

data.diagnosis()
with plt.rc_context(rc={"figure.max_open_warning": 0}):
    data.plot_qc_series()
    # data.plot_gaps(show=False)
    # data.plot_checks()
