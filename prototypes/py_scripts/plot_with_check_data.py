"""Using the utilities functions for various data sets."""

import matplotlib.pyplot as plt
from hilltoppy import web_service as ws

# Location and attributes of data to be obtained
base_url = "http://hilltopdev.horizons.govt.nz/"
base_hts = "RawLogger.hts"
check_hts = "Survey123.hts"
site = "Manawatu at Teachers College"
measurement = "Stage"
from_date = "2021-01-01 00:00"
to_date = "2023-10-12 8:30"
# Used only for the check data
item_name = "Internal S.G."

base_data = ws.get_data(
    base_url,
    base_hts,
    site,
    measurement,
    from_date,
    to_date,
)

check_data = ws.get_data(
    base_url,
    check_hts,
    site,
    measurement,
    from_date,
    to_date,
    tstype="Check",
    itemName=item_name,
)


plt.figure(figsize=(10, 6))
plt.subplot(1, 1, 1)
plt.plot(base_data["Time"], base_data["Value"], label="Original Data")
plt.plot(
    check_data["Time"],
    check_data["Value"],
    label="Check Data",
    marker="o",
    linestyle="None",
)
plt.legend()
plt.show()
