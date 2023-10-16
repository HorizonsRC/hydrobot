import matplotlib.pyplot as plt

import hydro_processing_tools.data_acquisition as data_acquisition
import hydro_processing_tools.utilities as utilities

if __name__ == "__main__":
    base_url = "http://tsdata.horizons.govt.nz/"
    hts = "boo.hts"
    site = "Saddle Road"
    measurement = "Groundwater"
    from_date = "2021-01-01 00:00"
    to_date = "2023-10-12 8:30"
    dtl_method = "trend"

    # Acquire the data
    data = data_acquisition.get_data(
        base_url, hts, site, measurement, from_date, to_date, dtl_method
    )

    plt.figure(figsize=(10, 6))
    plt.subplot(1, 1, 1)
    plt.plot(data["Value"], label="Original Data")
    plt.title("Data Before Spike Removal")
    plt.legend()

    # Perform spike removal using 'remove_spikes' function
    span = 10
    high_clip = 1000
    low_clip = -1000
    delta = 500
    cleaned_data = utilities.remove_spikes(
        data["Value"], span, high_clip, low_clip, delta
    )

    # Plot the data before and after spike removal
    # plt.figure(figsize=(10, 6))
    # plt.subplot(1, 1, 1)
    # plt.plot(data["Value"], label="Original Data")
    # plt.title("Data Before Spike Removal")
    # plt.legend()
    #
    # plt.plot(cleaned_data, label="Cleaned Data", color='orange')
    # plt.title("Data After Spike Removal")
    # plt.legend()

    plt.tight_layout()
    plt.show()
