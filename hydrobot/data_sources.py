"""Handling for different types of data sources."""
import csv
from pathlib import Path

import numpy as np
from annalist.annalist import Annalist

annalizer = Annalist()


class Measurement:
    """Basic measurement only compares magnitude of differences."""

    @annalizer.annalize
    def __init__(self, qc_500_limit, qc_600_limit, name=""):
        """Initialize Measurement."""
        self.qc_500_limit = qc_500_limit
        self.qc_600_limit = qc_600_limit
        self.name = name

    def __repr__(self):
        """Measurement representation."""
        return repr(f"Measurement '{self.name}' with limits {vars(self)}")

    @annalizer.annalize
    def find_qc(self, base_datum, check_datum):
        """Find the base quality codes."""
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

    @annalizer.annalize
    def __init__(
        self,
        qc_500_limit,
        qc_600_limit,
        qc_500_percent,
        qc_600_percent,
        limit_percent_threshold,
        name="",
    ):
        """Initialize TwoLevelMeasurement."""
        Measurement.__init__(self, qc_500_limit, qc_600_limit)
        # self.qc_500_limit = qc_500_limit
        # self.qc_600_limit = qc_600_limit
        self.qc_500_percent = qc_500_percent
        self.qc_600_percent = qc_600_percent
        self.limit_percent_threshold = limit_percent_threshold
        self.name = name

    @annalizer.annalize
    def find_qc(self, base_datum, check_datum):
        """Find the base quality codes with two a flat and percentage QC threshold."""
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


@annalizer.annalize
def get_measurement_dict():
    """
    Return all measurements in a dictionary.

    :return: dict of string:measurement pairs
    """
    measurement_dict = {}
    script_dir = Path(__file__).parent

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


@annalizer.annalize
def get_measurement(measurement_name):
    """
    Return measurement that matches the given name.

    Raises exception if measurement is not in the config.

    :param measurement_name: string
        Name of the measurement as defined in the config
    :return: Measurement
        The Measurement class initiated with the standard config data
    """
    m_dict = get_measurement_dict()
    if measurement_name in m_dict:
        return m_dict[measurement_name]
    else:
        raise Exception("Measurement not found in the config file")
