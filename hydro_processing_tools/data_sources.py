"""Handling for different types of data sources"""
import numpy as np
import csv
from pathlib import Path


class Measurement:
    """
    Basic measurement only compares magnitude of differences
    """

    def __init__(self, qc_500_limit, qc_600_limit):
        self.qc_500_limit = qc_500_limit
        self.qc_600_limit = qc_600_limit

    def find_qc(self, base_datum, check_datum):
        diff = np.abs(base_datum - check_datum)
        if diff < self.qc_600_limit:
            return 600
        elif diff < self.qc_500_limit:
            return 500
        else:
            return 400


def get_measurement_dict():
    """
    Returns all measurements in a dictionary
    :return: dict of string:measurement pairs
    """
    measurement_dict = {}
    script_dir = Path(__file__).parent
    template_path = (script_dir / "config/measurement_QC_config.csv").resolve()
    with open(template_path) as csv_file:
        reader = csv.reader(csv_file)

        for row in reader:
            measurement_dict[row[0]] = Measurement(float(row[1]), float(row[2]))
        csv_file.close()

    return measurement_dict


def get_measurement(measurement_name):
    """
    Returns measurement that matches the given name
    Raises exception if measurement is not in the config

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
