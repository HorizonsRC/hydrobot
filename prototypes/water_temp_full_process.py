"""
Script to run through various processing tasks
"""

import matplotlib.pyplot as plt
import pandas as pd
from hydro_processing_tools.data_acquisition import get_data
from hydro_processing_tools.filters import remove_spikes, clip
from hydro_processing_tools.evaluator import (
    check_data_quality_code,
    small_gap_closer,
    base_data_meets_qc,
)
from hydro_processing_tools.data_sources import get_measurement

# Location and attributes of data to be obtained
base_url = "http://hilltopdev.horizons.govt.nz/"
standard_hts = "RawLogger.hts"
check_hts = "boo.hts"

site = "Rangitikei at Mangaweka"
from_date = "2021-01-01 00:00"
to_date = "2023-10-12 8:30"

high_clip = 40
low_clip = 0
delta = 1
span = 10


# Measurements used
measurement = "Water Temperature [Dissolved Oxygen sensor]"
check_measurement = "Water Temperature Check [Water Temperature]"

base_data = get_data(
    base_url,
    standard_hts,
    site,
    measurement,
    from_date,
    to_date,
)
base_series = pd.Series(base_data["Value"].values, base_data["Time"])
base_series = base_series.asfreq("15T")
base_series.index.name = "Time"
base_series.name = "Value"

check_data = get_data(
    base_url,
    check_hts,
    site,
    check_measurement,
    from_date,
    to_date,
    tstype="Check",
)
check_series = pd.Series(check_data["Value"].values, check_data["Time"])
check_series.index.name = "Time"
check_series.name = "Value"
# Clip check data
check_series = clip(check_series, high_clip, low_clip)


# Removing spikes from base data
base_series = remove_spikes(base_series, span, high_clip, low_clip, delta)

# Removing small np.NaN gaps
base_series = small_gap_closer(base_series, 12)

# Find the QC values
qc_series = check_data_quality_code(
    base_series, check_series, get_measurement(measurement)
)
qc_series.index.name = "Time"
qc_series.name = "Value"

# Export the data
base_series.to_csv("output_dump/base_" + site + "-" + measurement + ".csv")
check_series.to_csv("output_dump/check_" + site + "-" + check_measurement + ".csv")
qc_series.to_csv("output_dump/QC_" + site + "-" + check_measurement + ".csv")

# filters for each QC
check_400 = check_series[qc_series == 400]
check_500 = check_series[qc_series == 500]
check_600 = check_series[qc_series == 600]
check_other = check_series[(qc_series != 400) & (qc_series != 500) & (qc_series != 600)]
base_400 = base_data_meets_qc(base_series, qc_series, 400)
base_500 = base_data_meets_qc(base_series, qc_series, 500)
base_600 = base_data_meets_qc(base_series, qc_series, 600)

plt.figure(figsize=(10, 6))
plt.subplot(1, 1, 1)
plt.plot(base_400.index, base_400, label="QC400", color="#ffa500")
plt.plot(base_500.index, base_500, label="QC500", color="#00bfff")
plt.plot(base_600.index, base_600, label="QC600", color="#006400")
plt.plot(
    check_series.index,
    check_series,
    label="Check data",
    marker="o",
    color="black",
    linestyle="None",
)

plt.legend()
plt.show()
