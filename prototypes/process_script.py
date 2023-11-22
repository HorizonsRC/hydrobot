"""Script to run through various processing tasks."""
import matplotlib.pyplot as plt
import pandas as pd
from hydrobot.data_acquisition import get_data
from hydrobot.filters import remove_spikes, clip
from hydrobot.evaluator import (
    check_data_quality_code,
    small_gap_closer,
    base_data_meets_qc,
    diagnose_data,
    missing_data_quality_code,
)
from hydrobot.data_sources import get_measurement
from annalist.annalist import Annalist


def process_data(processing_parameters):
    """Script to run through all processing."""
    # Location and attributes of data to be obtained

    ann = Annalist()
    ann.configure(
        logfile="output_dump/Processing Water Temp Data.",
        analyst_name="Hot Dameul, Sameul!",
    )

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
        processing_parameters["defaults"]["low_clip"],
        processing_parameters["defaults"]["high_clip"],
    )

    # Removing spikes from base data
    base_series = remove_spikes(
        base_series,
        processing_parameters["defaults"]["span"],
        processing_parameters["defaults"]["low_clip"],
        processing_parameters["defaults"]["high_clip"],
        processing_parameters["defaults"]["delta"],
    )

    # Removing small np.NaN gaps
    base_series = small_gap_closer(base_series, gap_limit=parameters["gap_limit"])

    # Find the QC values
    qc_series = check_data_quality_code(
        base_series, check_series, get_measurement(processing_parameters["measurement"])
    )
    qc_series = missing_data_quality_code(
        base_series, qc_series, gap_limit=parameters["gap_limit"]
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
    base_0 = base_data_meets_qc(base_series, qc_series, 0).asfreq(
        processing_parameters["frequency"]
    )
    base_100 = (
        base_data_meets_qc(base_series, qc_series, 100)
        .fillna(base_series.median())
        .asfreq(processing_parameters["frequency"])
    )
    base_200 = base_data_meets_qc(base_series, qc_series, 200).asfreq(
        processing_parameters["frequency"]
    )
    base_300 = base_data_meets_qc(base_series, qc_series, 300).asfreq(
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
            [base_600, base_500, base_400, base_300, base_200],
            [600, 500, 400, 300, 200],
            check_series,
        )
    )

    plt.figure(figsize=(10, 6))
    # plt.plot(base_series.index, base_series, label="All data") # for all data
    plt.plot(base_600.index, base_600, label="QC600", color="#006400")
    plt.plot(base_500.index, base_500, label="QC500", color="#00bfff")
    plt.plot(base_400.index, base_400, label="QC400", color="#ffa500")
    plt.plot(base_300.index, base_300, label="QC300", color="#d3d3d3")
    plt.plot(base_200.index, base_200, label="QC200", color="#8B5A00")
    plt.plot(
        base_100.index,
        base_100,
        marker="x",
        label="QC100",
        color="#ff0000",
    )
    plt.plot(base_0.index, base_0, label="QC0", color="#9900ff")
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


parameters = {
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
    "gap_limit": 12,
    "defaults": {
        "high_clip": 20000,
        "low_clip": 0,
        "delta": 1000,
        "span": 10,
    },
}

process_data(parameters)
