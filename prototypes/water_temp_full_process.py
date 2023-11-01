"""
Using the utilities functions for various data sets
"""

import matplotlib.pyplot as plt
import pandas as pd
from hilltoppy import Hilltop
from hydro_processing_tools.data_acquisition import get_data
from hydro_processing_tools.filters import remove_spikes, clip
from hydro_processing_tools.evaluator import check_data_quality_code, small_gap_closer
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

plt.figure(figsize=(10, 6))
plt.subplot(1, 1, 1)
plt.plot(base_series.index, base_series, label="Processed Data")
plt.plot(
    check_600.index,
    check_600,
    label="Check QC 600",
    marker="o",
    color="green",
    linestyle="None",
)
plt.plot(
    check_500.index,
    check_500,
    label="Check QC 500",
    marker="o",
    color="cyan",
    linestyle="None",
)
plt.plot(
    check_400.index,
    check_400,
    label="Check QC 400",
    marker="o",
    color="yellow",
    linestyle="None",
)
plt.plot(
    check_other.index,
    check_other,
    label="Check QC>=300",
    marker="o",
    color="brown",
    linestyle="None",
)
plt.legend()
plt.show()
