"""Handling for different types of data sources."""
import csv
from pathlib import Path
import pandas as pd
import re

import numpy as np


class Measurement:
    """Basic measurement only compares magnitude of differences."""

    def __init__(self, qc_500_limit, qc_600_limit, name=""):
        """
        Initialize Measurement.

        Parameters
        ----------
        qc_500_limit : numerical
            Threshold between QC 400 and QC 500
        qc_600_limit : numerical
            Threshold between QC 500 and QC 600
        name : str
            Name of the data source
        """
        self.qc_500_limit = qc_500_limit
        self.qc_600_limit = qc_600_limit
        self.name = name

    def __repr__(self):
        """Measurement representation."""
        return repr(f"Measurement '{self.name}'")

    def find_qc(self, base_datum, check_datum):
        """
        Find the base quality codes.

        Parameters
        ----------
        base_datum : numerical
            Closest continuum datum point to the check
        check_datum : numerical
            The check data to verify the continuous data

        Returns
        -------
        int
            The Quality code

        """
        diff = np.abs(base_datum - check_datum)
        if diff < self.qc_600_limit:
            return 600
        elif diff < self.qc_500_limit:
            return 500
        else:
            return 400


class TwoLevelMeasurement(Measurement):
    """
    Measurement for standards such as water level.

    Fixed error up to given threshold, percentage error after that.
    """

    def __init__(
        self,
        qc_500_limit,
        qc_600_limit,
        qc_500_percent,
        qc_600_percent,
        limit_percent_threshold,
        name="",
    ):
        """
        Initialize TwoLevelMeasurement.

        Parameters
        ----------
        qc_500_limit : numerical
            Threshold between QC 400 and QC 500 for linear portion
        qc_600_limit : numerical
            Threshold between QC 500 and QC 600 for linear portion
        qc_500_percent : numerical
            Threshold between QC 400 and QC 500 for percentage portion
        qc_600_percent : numerical
            Threshold between QC 500 and QC 600 for percentage portion
        limit_percent_threshold
            Value at which the measurement transitions between linear and percentage QC comparison
        name : str
            Name of the data source
        """
        Measurement.__init__(self, qc_500_limit, qc_600_limit)
        # self.qc_500_limit = qc_500_limit
        # self.qc_600_limit = qc_600_limit
        self.qc_500_percent = qc_500_percent
        self.qc_600_percent = qc_600_percent
        self.limit_percent_threshold = limit_percent_threshold
        self.name = name

    def find_qc(self, base_datum, check_datum):
        """
        Find the base quality codes with two stages - a flat and percentage QC threshold.

        Parameters
        ----------
        base_datum : numerical
            Closest continuum datum point to the check
        check_datum : numerical
            The check data to verify the continuous data

        Returns
        -------
        int
            The Quality code

        """
        if base_datum < self.limit_percent_threshold:
            # flat qc check
            diff = np.abs(base_datum - check_datum)
            if diff < self.qc_600_limit:
                return 600
            elif diff < self.qc_500_limit:
                return 500
            else:
                return 400
        else:
            # percent qc check
            diff = np.abs(base_datum / check_datum - 1) * 100
            if diff < self.qc_600_percent:
                return 600
            elif diff < self.qc_500_percent:
                return 500
            else:
                return 400


def get_measurement_dict():
    """
    Return all measurements in a dictionary.

    Returns
    -------
    dict of string-measurement pairs
    """
    measurement_dict = {}
    script_dir = Path(__file__).parent
    # script_dir = os.path.dirname(os.path.abspath(__file__))

    # Plain Measurements
    template_path = (script_dir / "config/measurement_QC_config.csv").resolve()
    with open(template_path) as csv_file:
        reader = csv.reader(csv_file)

        for row in reader:
            measurement_dict[row[0]] = Measurement(float(row[1]), float(row[2]), row[0])
        csv_file.close()

    # Two stage Measurements
    template_path = (script_dir / "config/TwoLevelMeasurement_QC_config.csv").resolve()
    with open(template_path) as csv_file:
        reader = csv.reader(csv_file)

        for row in reader:
            measurement_dict[row[0]] = TwoLevelMeasurement(
                float(row[1]),
                float(row[2]),
                float(row[3]),
                float(row[4]),
                float(row[5]),
                row[0],
            )
        csv_file.close()

    return measurement_dict


def get_measurement(measurement_name):
    """
    Return measurement that matches the given name.

    Raises exception if measurement is not in the config.

    Parameters
    ----------
    measurement_name : string
        Name of the measurement as defined in the config

    Returns
    -------
    Measurement
        The Measurement class initiated with the standard config data
    """
    m_dict = get_measurement_dict()
    if measurement_name in m_dict:
        return m_dict[measurement_name]
    else:
        raise Exception(
            f"Measurement {measurement_name} not found in the config file. "
            f"Available measurements are {list(m_dict.keys())}."
        )


def series_export_to_csv(
    file_location: str,
    site_name: str,
    measurement_name: str,
    std_series: pd.Series | None,
    check_series: pd.Series | None,
    qc_series: pd.Series | None,
):
    """
    Export the 3 main series to csv.

    Parameters
    ----------
    file_location : str
        Where the files are exported to
    site_name : str
        Site name
    measurement_name : str
        Measurement name
    std_series : pd.Series
        Standard series
    check_series : pd.Series
        Check series
    qc_series : pd.Series
        Quality code series
    Returns
    -------
    None, but makes files
    """
    if std_series is not None:
        std_series.to_csv(
            file_location
            + "std_"
            + site_name
            + "-"
            + re.sub("[^A-Za-z0-9]+", "_", measurement_name)
            + ".csv"
        )
    if check_series is not None:
        check_series.to_csv(
            file_location
            + "check_"
            + site_name
            + "-"
            + re.sub("[^A-Za-z0-9]+", "_", measurement_name)
            + ".csv"
        )
    if qc_series is not None:
        qc_series.to_csv(
            file_location
            + "QC_"
            + site_name
            + "-"
            + re.sub("[^A-Za-z0-9]+", "_", measurement_name)
            + ".csv"
        )
