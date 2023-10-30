"""
Using the utilities functions for various data sets
"""

import matplotlib.pyplot as plt
from hilltoppy import Hilltop
from hydro_processing_tools.data_acquisition import get_data
from hydro_processing_tools.filters import remove_spikes, clip

# Location and attributes of data to be obtained
base_url = "http://hilltopdev.horizons.govt.nz/"
standard_hts = "RawLogger.hts"
check_hts = "boo.hts"

site = "Manawatu at Teachers College"
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

check_data = get_data(
    base_url,
    check_hts,
    site,
    check_measurement,
    from_date,
    to_date,
    tstype="Check",
)
# Clip check data

check_data["Value"] = clip(check_data["Value"], high_clip, low_clip)


# Removing spikes from base data
processed_data = base_data
processed_data["Value"] = remove_spikes(
    processed_data["Value"], span, high_clip, low_clip, delta
)

processed_data.to_csv("output_dump/base_" + site + "-" + measurement + ".csv")
check_data.to_csv("output_dump/check_" + site + "-" + check_measurement + ".csv")

plt.figure(figsize=(10, 6))
plt.subplot(1, 1, 1)
plt.plot(processed_data["Time"], processed_data["Value"], label="Original Data")
plt.plot(
    check_data["Time"],
    check_data["Value"],
    label="Check Data",
    marker="o",
    linestyle="None",
)
plt.legend()
plt.show()
