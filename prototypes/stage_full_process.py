"""Script to run through various processing tasks."""
import time
import matplotlib.pyplot as plt
import pandas as pd
from hydrobot.data_acquisition import get_data
from hydrobot.filters import remove_spikes, clip
from hydrobot.evaluator import (
    check_data_quality_code,
    small_gap_closer,
    base_data_meets_qc,
    diagnose_data,
)
from hydrobot.data_sources import get_measurement
from annalist.annalist import Annalist

# Location and attributes of data to be obtained
base_url = "http://hilltopdev.horizons.govt.nz/"
standard_hts = "RawLogger.hts"
check_hts = "boo.hts"

site = "Whanganui at Te Rewa"
from_date = "2021-01-01 00:00"
to_date = "2023-10-12 8:30"
frequency = "5T"

high_clip = 20000
low_clip = 0
delta = 1000
span = 10

# Measurements used
measurement = "Water level statistics: Point Sample"
check_measurement = "External S.G. [Water Level NRT]"

ann = Annalist()
ann.configure("Processing Water Temp Data.", "Hot Dameul, Sameul!")

base_data = get_data(
    base_url,
    standard_hts,
    site,
    measurement,
    from_date,
    to_date,
)
base_series = pd.Series(base_data["Value"].values, base_data["Time"])
base_series = base_series.asfreq(frequency)
raw_data = base_series

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
check_series = clip(check_series, low_clip, high_clip)

# Removing spikes from base data
base_series = remove_spikes(base_series, span, low_clip, high_clip, delta)

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
base_200 = base_data_meets_qc(base_series, qc_series, 200).asfreq(frequency)
base_400 = base_data_meets_qc(base_series, qc_series, 400).asfreq(frequency)
base_500 = base_data_meets_qc(base_series, qc_series, 500).asfreq(frequency)
base_600 = base_data_meets_qc(base_series, qc_series, 600).asfreq(frequency)


print(
    diagnose_data(
        raw_data,
        base_series,
        [base_600, base_500, base_400, base_200],
        [600, 500, 400, 200],
        check_series,
    )
)

plt.figure(figsize=(10, 6))
# plt.plot(base_series.index, base_series, label="All data") # for all data
plt.plot(base_600.index, base_600, label="QC600", color="#006400")
plt.plot(base_500.index, base_500, label="QC500", color="#00bfff")
plt.plot(base_400.index, base_400, label="QC400", color="#ffa500")
plt.plot(base_200.index, base_200, label="QC200", color="#8b5902")
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
