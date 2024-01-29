"""Example script."""

import json

import matplotlib as plt
from annalist.annalist import Annalist

from hydrobot.processor import Processor

with open("site_parameters.json") as json_file:
    lines = [line for line in json_file]
    data = []
    for line in lines:
        data.append(json.loads(line))

processing_parameters = data[0]
print(processing_parameters["site"])

ann = Annalist()
stream_format_str = (
    "%(asctime)s, %(analyst_name)s, %(function_name)s, %(site)s, %(measurement)s, ts_type, "
    "%(from_date)s, %(to_date)s, %(message)s"
)
ann.configure(
    logfile="output_dump/bot_annals.csv",
    analyst_name="Sam Irvine",
    file_format_str=stream_format_str,
)

data = Processor(
    processing_parameters["base_url"],
    processing_parameters["site"],
    processing_parameters["standard_hts_filename"],
    processing_parameters["standard_measurement_name"],
    processing_parameters["frequency"],
    processing_parameters["from_date"],
    processing_parameters["to_date"],
    processing_parameters["check_hts_filename"],
    processing_parameters["check_measurement_name"],
    processing_parameters["defaults"],
)


data.clip()
data.remove_spikes()
data.gap_closer()
data.quality_encoder()

data.data_exporter("output_dump/")

data.diagnosis()
with plt.rc_context(rc={"figure.max_open_warning": 0}):
    data.plot_qc_series()
    # data.plot_gaps(show=False)
    # data.plot_checks()
