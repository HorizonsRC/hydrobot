"""
Using the utilities functions for various data sets
"""

import matplotlib.pyplot as plt
from hilltoppy import Hilltop

# Location and attributes of data to be obtained
base_url = "http://hilltopdev.horizons.govt.nz/"
base_hts = "RawLogger.hts"
ht_base = Hilltop(base_url, base_hts)
check_hts = "boo.hts"
ht_check = Hilltop(base_url, check_hts)


# awfa

site = "Manawatu at Teachers College"
from_date = "2021-01-01 00:00"
to_date = "2023-10-12 8:30"


# Measurements used
measurement = "Water Temperature [Dissolved Oxygen sensor]"
check_measurement = "Water Temperature Check [Water Temperature]"

base_data = ht_base.get_data(
    site,
    measurement,
    from_date,
    to_date,
)

check_data = ht_check.get_data(
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
