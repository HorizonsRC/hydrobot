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

# Choose whether to display extra plots
display_working_plots = False

# Obtain data
data = data_acquisition.get_data(
    base_url, hts, site, measurement, from_date, to_date, "standard"
)


# Base data display
if display_working_plots:
    plt.figure(figsize=(10, 6))
    plt.subplot(1, 1, 1)
    plt.plot(data["Value"], label="Original Data")
    plt.title("Data before spike removal")
    plt.legend()


# Remove high values and low values
clip_data = filters.clip(data["Value"], high_clip, low_clip)

# Base vs clipped data display
if display_working_plots:
    plt.figure(figsize=(10, 6))
    plt.subplot(1, 1, 1)
    plt.plot(data["Value"], label="Original Data")
    plt.plot(clip_data, label="Clipped Data")
    plt.legend()

# Create smoothed data using forwards-backwards exponential weighted moving
# average (FBEWMA)
fbewma_data = filters.fbewma(clip_data, span)

# Base vs smoothed data
if display_working_plots:
    plt.figure(figsize=(10, 6))
    plt.subplot(1, 1, 1)
    plt.plot(data["Value"], label="Original Data")
    plt.plot(fbewma_data, label="FBEWMA Data")
    plt.legend()


# Compare base data to smoothed data, remove any large differences
delta_clip_data = filters.remove_outliers(clip_data, span, delta)

# Display cleaned data
plt.figure(figsize=(10, 6))
plt.subplot(1, 1, 1)
plt.plot(data["Value"], label="Original Data")
plt.plot(delta_clip_data, label="Cleaned Data")
plt.legend()
plt.show()
