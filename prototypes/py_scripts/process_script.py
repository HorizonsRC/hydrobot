"""Script to run through various processing tasks."""
import matplotlib.pyplot as plt
import pandas as pd

# import pandas as pd
from annalist.annalist import Annalist

import hydrobot.plotter as plotter
from hydrobot.data_acquisition import get_series
from hydrobot.data_sources import get_qc_evaluator
from hydrobot.evaluator import diagnose_data, quality_encoder, small_gap_closer
from hydrobot.filters import clip, remove_spikes


def process_data(processing_parameters):
    """Script to run through all processing."""
    # Location and attributes of data to be obtained

    ann = Annalist()
    ann.configure(
        logfile="output_dump/Processing Water Temp Data.",
        analyst_name="Hot Dameul, Sameul!",
    )

    base_series = get_series(
        processing_parameters["base_url"],
        processing_parameters["standard_hts_filename"],
        processing_parameters["site"],
        processing_parameters["standard_measurement_name"],
        processing_parameters["from_date"],
        processing_parameters["to_date"],
    )
    base_series = base_series.asfreq(processing_parameters["frequency"])
    if not isinstance(base_series, pd.Series):
        raise TypeError("This should be a pd.Series, but it's a pd.DataFrame")

    check_data = get_series(
        processing_parameters["base_url"],
        processing_parameters["check_hts_filename"],
        processing_parameters["site"],
        processing_parameters["check_measurement_name"],
        processing_parameters["from_date"],
        processing_parameters["to_date"],
        tstype="Check",
    )
    if not isinstance(base_series, pd.Series):
        raise TypeError("This should be a pd.Series, but it's a pd.DataFrame")

    # Clip check data
    check_series = clip(
        pd.Series(check_data["Check Guage Total"]),
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
    base_series = small_gap_closer(
        base_series, gap_limit=parameters["defaults"]["gap_limit"]
    )

    # Find the QC values
    qc_series = quality_encoder(
        base_series,
        check_series,
        get_qc_evaluator(processing_parameters["standard_measurement_name"]),
        gap_limit=parameters["defaults"]["gap_limit"],
    )

    # Export the data
    base_series.to_csv(
        "output_dump/base_"
        + processing_parameters["site"]
        + "-"
        + processing_parameters["standard_measurement_name"]
        + ".csv"
    )
    check_series.to_csv(
        "output_dump/check_"
        + processing_parameters["site"]
        + "-"
        + processing_parameters["check_measurement_name"]
        + ".csv"
    )
    qc_series.to_csv(
        "output_dump/QC_"
        + processing_parameters["site"]
        + "-"
        + processing_parameters["standard_measurement_name"]
        + ".csv"
    )

    diagnose_data(
        base_series,
        check_series,
        qc_series,
        parameters["frequency"],
    )
    with plt.rc_context(rc={"figure.max_open_warning": 0}):
        plotter.qc_plotter(
            base_series, check_series, qc_series, parameters["frequency"], show=False
        )
        plotter.check_plotter(base_series, check_series, show=False)
        plotter.gap_plotter(base_series)


parameters = {
    "base_url": "http://hilltopdev.horizons.govt.nz/",
    "standard_hts_filename": "RawLogger.hts",
    "check_hts_filename": "boo.hts",
    "site": "Whanganui at Te Rewa",
    "from_date": "2021-06-01 00:00",
    "to_date": "2023-08-12 8:30",
    "frequency": "5T",
    "standard_measurement_name": "Water level statistics: Point Sample",
    "check_measurement_name": "External S.G. [Water Level NRT]",
    "defaults": {
        "high_clip": 20000,
        "low_clip": 0,
        "delta": 1000,
        "span": 10,
        "gap_limit": 12,
    },
}

process_data(parameters)
