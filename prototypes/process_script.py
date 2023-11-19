"""
Script to run through various processing tasks
"""
import matplotlib.pyplot as plt
import pandas as pd
from hydro_processing_tools.data_acquisition import get_data
from hydro_processing_tools.filters import remove_spikes, clip
from hydro_processing_tools.evaluator import (
    check_data_quality_code,
    small_gap_closer,
    base_data_meets_qc,
    diagnose_data,
)
from hydro_processing_tools.data_sources import get_measurement
from annalist.annalist import Annalist


def process_data(processing_parameters):
    # Location and attributes of data to be obtained

    ann = Annalist()
    ann.configure("Processing Water Temp Data.", "Hot Dameul, Sameul!")

    base_data = get_data(
        processing_parameters["standard_base_url"],
        processing_parameters["standard_hts_filename"],
        processing_parameters["site"],
        processing_parameters["measurement"],
        processing_parameters["from_date"],
        processing_parameters["to_date"],
    )
    base_series = pd.Series(base_data["Value"].values, base_data["Time"])
    base_series = base_series.asfreq(processing_parameters["frequency"])
    raw_data = base_series

    base_series.index.name = "Time"
    base_series.name = "Value"

    check_data = get_data(
        processing_parameters["check_base_url"],
        processing_parameters["check_hts_filename"],
        processing_parameters["site"],
        processing_parameters["check_measurement"],
        processing_parameters["from_date"],
        processing_parameters["to_date"],
        tstype="Check",
    )
    check_series = pd.Series(check_data["Value"].values, check_data["Time"])
    check_series.index.name = "Time"
    check_series.name = "Value"
    # Clip check data
    check_series = clip(
        check_series,
        processing_parameters["low_clip"],
        processing_parameters["high_clip"],
    )

    # Removing spikes from base data
    base_series = remove_spikes(
        base_series,
        processing_parameters["span"],
        processing_parameters["low_clip"],
        processing_parameters["high_clip"],
        processing_parameters["delta"],
    )

    # Removing small np.NaN gaps
    base_series = small_gap_closer(base_series, 12)

    print(base_series)
    print(check_series)
    # Find the QC values
    qc_series = check_data_quality_code(
        base_series, check_series, get_measurement(processing_parameters["measurement"])
    )
    qc_series.index.name = "Time"
    qc_series.name = "Value"

    # Export the data
    base_series.to_csv(
        "output_dump/base_"
        + processing_parameters["site"]
        + "-"
        + processing_parameters["measurement"]
        + ".csv"
    )
    check_series.to_csv(
        "output_dump/check_"
        + processing_parameters["site"]
        + "-"
        + processing_parameters["check_measurement"]
        + ".csv"
    )
    qc_series.to_csv(
        "output_dump/QC_"
        + processing_parameters["site"]
        + "-"
        + processing_parameters["check_measurement"]
        + ".csv"
    )

    # filters for each QC
    base_200 = base_data_meets_qc(base_series, qc_series, 200).asfreq(
        processing_parameters["frequency"]
    )
    base_400 = base_data_meets_qc(base_series, qc_series, 400).asfreq(
        processing_parameters["frequency"]
    )
    base_500 = base_data_meets_qc(base_series, qc_series, 500).asfreq(
        processing_parameters["frequency"]
    )
    base_600 = base_data_meets_qc(base_series, qc_series, 600).asfreq(
        processing_parameters["frequency"]
    )

    print(
        diagnose_data(
            raw_data,
            base_series,
            [base_600, base_500, base_400, base_200],
            [600, 500, 400, 200],
            check_series,
        )
    )

    plt.figure(figsize=(10, 6))
    # plt.plot(base_series.index, base_series, label="All data") # for all data
    plt.plot(base_600.index, base_600, label="QC600", color="#006400")
    plt.plot(base_500.index, base_500, label="QC500", color="#00bfff")
    plt.plot(base_400.index, base_400, label="QC400", color="#ffa500")
    plt.plot(base_200.index, base_200, label="QC200", color="#8b5902")
    plt.plot(
        check_series.index,
        check_series,
        label="Check data",
        marker="o",
        color="black",
        linestyle="None",
    )

    plt.legend()
    plt.show()


processing_parameters = {
    "standard_base_url": "http://hilltopdev.horizons.govt.nz/",
    "check_base_url": "http://hilltopdev.horizons.govt.nz/",
    "standard_hts_filename": "RawLogger.hts",
    "check_hts_filename": "boo.hts",
    "site": "Whanganui at Te Rewa",
    "from_date": "2021-06-01 00:00",
    "to_date": "2023-08-12 8:30",
    "frequency": "5T",
    "measurement": "Water level statistics: Point Sample",
    "check_measurement": "External S.G. [Water Level NRT]",
    "high_clip": 20000,
    "low_clip": 0,
    "delta": 1000,
    "span": 10,
}

process_data(processing_parameters)
