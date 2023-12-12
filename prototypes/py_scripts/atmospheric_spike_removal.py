"""Atmospheric Spike Removal."""
# %% [markdown]
# # Saddle Road Spike Removal Test

import matplotlib.pyplot as plt

import hydrobot.data_acquisition as data_acquisition
import hydrobot.filters as filters

# %%
base_url = "http://hilltopdev.horizons.govt.nz/"
hts = "RawLoggerNet.hts"
site = "Manawatu at Weber Road"
measurement = "Atmospheric Pressure"
from_date = "2021-01-01 00:00"
to_date = "2023-10-12 8:30"
dtl_method = "trend"

# %%
data = data_acquisition.get_data(
    base_url, hts, site, measurement, from_date, to_date, dtl_method
)
print(data)
# print(data)

# %%
plt.figure(figsize=(10, 6))
plt.subplot(1, 1, 1)
plt.plot(data["Value"], label="Original Data")
plt.title("Data before spike removal")
plt.legend()


# %% [markdown]
# ## Spike removal parameters

# %%
span = 10
high_clip = 1100
low_clip = 900
delta = 20


# %%
clip_data = filters.clip(data["Value"], high_clip, low_clip)

# %%
plt.figure(figsize=(10, 6))
plt.subplot(1, 1, 1)
plt.plot(data["Value"], label="Original Data")
plt.plot(clip_data, label="Clipped Data")
plt.legend()

# %%
fbewma_data = filters.fbewma(clip_data, span)

# %%
plt.figure(figsize=(10, 6))
plt.subplot(1, 1, 1)
plt.plot(data["Value"], label="Original Data")
plt.plot(fbewma_data, label="FBEWMA Data")
plt.legend()


# %%
delta_clip_data = filters.remove_outliers(data["Value"], span, delta)

# %%
plt.figure(figsize=(10, 6))
plt.subplot(1, 1, 1)
plt.plot(data["Value"], label="Original Data")
plt.plot(delta_clip_data, label="Cleaned Data")
plt.legend()
plt.show()
