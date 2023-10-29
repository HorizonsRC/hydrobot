"""
Using the utilities functions for various data sets
"""

import matplotlib.pyplot as plt
from hilltoppy import Hilltop
from hydro_processing_tools.data_acquisition import get_data

# Location and attributes of data to be obtained
base_url = "http://hilltopdev.horizons.govt.nz/"
standard_hts = "RawLogger.hts"
check_hts = "boo.hts"


# awfa

site = "Manawatu at Teachers College"
from_date = "2021-01-01 00:00"
to_date = "2023-10-12 8:30"


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
filtered_check_data = check_data[check_data["Value"] != -1]

plt.figure(figsize=(10, 6))
plt.subplot(1, 1, 1)
plt.plot(base_data["Time"], base_data["Value"], label="Original Data")
plt.plot(
    filtered_check_data["Time"],
    filtered_check_data["Value"],
    label="Check Data",
    marker="o",
    linestyle="None",
)
plt.legend()
plt.show()

base_data.to_csv("output_dump/base_" + site + "-" + measurement)
check_data.to_csv("output_dump/check_" + site + "-" + check_measurement)
