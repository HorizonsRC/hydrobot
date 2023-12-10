"""Gap Finder Script."""
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from hydrobot.data_acquisition import get_data

base_url = "http://hilltopdev.horizons.govt.nz/"
standard_hts = "RawLogger.hts"
site = "Manawatu at Foxton"
measurement = "Atmospheric Pressure"
from_date = "2021-01-01 00:00"
to_date = "2023-10-12 8:30"

base_data = get_data(
    base_url,
    standard_hts,
    site,
    measurement,
    from_date,
    to_date,
)

base_data = base_data.set_index("Time")
base_data.index = pd.to_datetime(base_data.index)
base_data = base_data.asfreq("15T")

base_data.loc["2023-04-01 13:00:00"] = pd.NA
print(f"Missing datastamps: {base_data['Value'].isna()}")
print(base_data[(base_data.Value.isna()) & ~(base_data.Value.shift().isna())])
gaps = len(base_data[(base_data.Value.isna()) & ~(base_data.Value.shift().isna())])
print(f"Gaps: {gaps}")
thresh = 3


idx0 = np.flatnonzero(np.r_[True, np.diff(np.isnan(base_data["Value"])) != 0, True])
count = np.diff(idx0)
idx = idx0[:-1]
valid_mask = np.isnan(base_data["Value"][idx])
out_idx = idx[valid_mask]
out_count = count[valid_mask]
out = zip(base_data.index[out_idx], out_count)
print([o for o in out])


nans = base_data[base_data["Value"].isna()]
fake_nans = nans
fake_nans["Value"] = 1000

plt.figure(figsize=(10, 6))
plt.plot(base_data["Value"], label="Data")
plt.plot(
    fake_nans["Value"],
    color="red",
    marker="|",
    linestyle="None",
    label="Gaps",
    markersize=100,
)
plt.title(f"Gaps in da data = {base_data['Value'].isna().sum()}")
plt.legend()
plt.show()
