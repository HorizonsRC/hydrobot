"""Using the filters functions for various data sets."""

import matplotlib.pyplot as plt

import hydrobot.data_acquisition as data_acquisition
import hydrobot.filters as filters

# Location and attributes of data to be obtained
base_url = "http://hilltopdev.horizons.govt.nz/"
hts = "RawLoggerNet.hts"
site = "HDC Foxton Beach 1"
measurement = "Water Temperature"
from_date = "2021-01-01 00:00"
to_date = "2023-10-12 8:30"

# Spike removal parameters
span = 10
high_clip = 40
low_clip = 0
delta = 1

# Obtain data
data = data_acquisition.get_data(
    base_url, hts, site, measurement, from_date, to_date, "standard"
)


# Remove high values and low values
cleaned_data = filters.remove_spikes(data["Value"], span, high_clip, low_clip, delta)

# Display cleaned data
plt.figure(figsize=(10, 6))
plt.subplot(1, 1, 1)
plt.plot(data["Value"], label="Original Data")
plt.plot(cleaned_data, label="Cleaned Data")
plt.legend()
plt.show()
