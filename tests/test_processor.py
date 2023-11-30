import random
from datetime import datetime, timedelta

import pandas as pd
import pytest
from annalist.annalist import Annalist
from hilltoppy import Hilltop

from hydrobot import processor

ann = Annalist()
ann.configure()

SITES = [
    "Slimy Bog at Dirt Road",
    "Mid Stream at Cowtoilet Farm",
    "Mostly Cowpiss River at Greenwash Pastures",
]

MEASUREMENTS = [
    "General Nastiness (out of 10)",
    "Atmospheric Pressure",
    "Number of Actual Whole Turds Floating By (t/s)",
    "Dead Cow Concentration (ppm)",
]


@pytest.fixture(autouse=True)
def no_requests(monkeypatch):
    """Don't allow requests to make requests."""
    monkeypatch.delattr("requests.sessions.Session.request")


@pytest.fixture
def mock_site_list():
    """Mock response from SiteList server call method."""
    data = {
        "SiteName": SITES,
    }

    df = pd.DataFrame(data)
    return df


@pytest.fixture
def mock_measurement_list():
    """Mock response from MeasurementList server call method."""
    data = {
        "MeasurementName": MEASUREMENTS,
    }

    df = pd.DataFrame(data)
    return df


@pytest.fixture
def mock_dataset():
    """Mock response from GetData server call method"""

    num_obs = 5
    random.seed(69420)

    site_name = SITES[1]
    measurement_name = MEASUREMENTS[1]
    start_time = datetime(2020, 10, 1, 8, 0, 0)
    time_intervals = [start_time + timedelta(minutes=i * 5) for i in range(num_obs)]
    values = [random.uniform(0, 100) * 10000 for _ in range(num_obs)]
    data = {
        "SiteName": [site_name] * num_obs,
        "MeasurementName": [measurement_name] * num_obs,
        "Time": [str(time) for time in time_intervals],
        "Value": values,
    }

    df = pd.DataFrame(data)
    return df


def test_processor(monkeypatch, mock_site_list, mock_measurement_list, mock_dataset):
    """Test the processor function."""

    def get_mock_site_list(*args, **kwargs):
        return mock_site_list

    def get_mock_measurement_list(*args, **kwargs):
        return mock_measurement_list

    def get_mock_dataset(*args, **kwargs):
        return mock_dataset

    monkeypatch.setattr(Hilltop, "get_site_list", get_mock_site_list)
    monkeypatch.setattr(Hilltop, "get_measurement_list", get_mock_measurement_list)
    monkeypatch.setattr(Hilltop, "get_data", get_mock_dataset)

    pr = processor.Processor(
        "https://greenwashed.and.pleasant/",
        SITES[1],
        "GreenPasturesAreNaturalAndEcoFriendlyISwear.hts",
        MEASUREMENTS[1],
        "5T",
    )
    print(pr.standard_series.loc["2020-10-01 08:00:00"])
    # assert pr.standard_series.loc["2020-10-01 08:00:00"] ==
