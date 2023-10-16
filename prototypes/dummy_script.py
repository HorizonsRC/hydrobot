# %% [markdown]
# # Saddle Road Spike Removal Test

# %%
import matplotlib

matplotlib.use("module://ipympl.backend_nbagg")
import hilltoppy
import matplotlib.pyplot as plt

import hydro_processing_tools.data_acquisition as data_acquisition
import hydro_processing_tools.utilities as utilities

# %%
base_url = "http://tsdata.horizons.govt.nz/"
hts = "boo.hts"
site = "Saddle Road"
measurement = "Groundwater"
from_date = "2021-01-01 00:00"
to_date = "2023-10-12 8:30"
dtl_method = "trend"

# %%
data = data_acquisition.get_data(
    base_url, hts, site, measurement, from_date, to_date, dtl_method
)
print(data)

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
high_clip = 3500
low_clip = 0
delta = 500


# Bad comment
# BADDER COMMENT
# %%
clip_data = smooth.clip(data["Value"], high_clip, low_clip)

# %%
plt.figure(figsize=(10, 6))
plt.subplot(1, 1, 1)
plt.plot(data["Value"], label="Original Data")
plt.plot(clip_data, label="Clipped Data")
plt.legend()

# %%
fbewma_data = smooth.fbewma(clip_data, span)

# %%
plt.figure(figsize=(10, 6))
plt.subplot(1, 1, 1)
plt.plot(data["Value"], label="Original Data")
plt.plot(fbewma_data, label="FBEWMA Data")
plt.legend()

# %%
