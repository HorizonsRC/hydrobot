"""Missing record script."""
import csv

import numpy as np
import pandas as pd
import yaml

from hydrobot.data_acquisition import get_data
from hydrobot.utils import infer_frequency

with open("script_config.yaml") as file:
    config = yaml.safe_load(file)


def report_missing_record(site, measurement, start, end):
    """Reports minutes missing."""
    _, blob = get_data(
        config["base_url"],
        config["hts"],
        site,
        measurement,
        start,
        end,
    )

    if blob is None or len(blob) == 0:
        return np.nan

    series = blob[0].data.timeseries[blob[0].data.timeseries.columns[0]]
    series.index = pd.DatetimeIndex(series.index)

    freq = infer_frequency(series, method="mode")
    series = series.reindex(pd.date_range(start, end, freq=freq))
    missing_points = series.asfreq(freq).isna().sum()
    return missing_points


a = {}
for site in config["sites"]:
    b = []
    for meas in config["measurements"]:
        b.append(report_missing_record(site, meas, config["start"], config["end"]))
    a[site] = b

with open("output_dump/output.csv", "w", newline="") as output:
    wr = csv.writer(output)
    wr.writerow(["Sites"] + config["measurements"])
    for site in a:
        wr.writerow([site] + a[site])
