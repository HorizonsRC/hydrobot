import math

import numpy as np
import pandas as pd
import pytest
from annalist.annalist import Annalist

import hydrobot.filters as filters

ann = Annalist()
ann.configure()

raw_data_dict = {
    "2021-01-01 00:00": 1.0,
    "2021-01-01 00:05": 2.0,
    "2021-01-01 00:10": 10.0,
    "2021-01-01 00:15": 4.0,
    "2021-01-01 00:20": 5.0,
}

fbewma_data_dict = {
    "2021-01-01 00:00": 1.870968,
    "2021-01-01 00:05": 3.133333,
    "2021-01-01 00:10": 7.0,
    "2021-01-01 00:15": 4.733333,
    "2021-01-01 00:20": 5.032258,
}


@pytest.fixture
def raw_data():
    """Example data for testing. Do not change these values!"""
    # Allows parametrization with a list of keys to change to np.nan
    data_series = pd.Series(raw_data_dict)
    return data_series


def insert_raw_data_gaps(gaps):
    for gap in gaps:
        raw_data_dict[gap] = np.nan
    data_series = pd.Series(raw_data_dict)
    return data_series


@pytest.fixture
def fbewma_data():
    """Mock function returning correct values for fbewma running on one_outlier_data with span=4"""
    data_series = pd.Series(fbewma_data_dict)
    return data_series


def insert_fbewma_data_gaps(gaps):
    for gap in gaps:
        fbewma_data_dict[gap] = np.nan
    data_series = pd.Series(fbewma_data_dict)
    return data_series


# Actual tests begin here:
##########################


def test_clip(raw_data):
    # Setup
    low_clip = 2
    high_clip = 4

    # Testing
    clipped = filters.clip(raw_data, low_clip, high_clip)

    assert math.isnan(clipped["2021-01-01 00:00"]), "Low value not removed!"
    assert math.isnan(clipped["2021-01-01 00:20"]), "High value not removed!"
    assert not (
        math.isnan(clipped["2021-01-01 00:20"])
        and math.isnan(clipped["2021-01-01 00:05"])
    ), "Border value removed (should not be)!"


def test_fbewma(raw_data, fbewma_data):
    # Setup
    span = 3

    # Testing
    fbewmadf = filters.fbewma(raw_data, span)

    # pytest.approx accounts for floating point errors and such
    assert fbewmadf.values == pytest.approx(fbewma_data.values), "FBEWMA failed!"


def test_remove_outliers(raw_data, fbewma_data, mocker, span=2, delta=2):
    # Setting up a bug free mock version of fbewma to use in remove_outliers
    fbewma_mock = mocker.patch(
        "hydrobot.filters.fbewma",
        side_effect=fbewma_data,
    )

    # This call of remove outliers should call fbewma_mock in the place of fbewma
    no_outliers = filters.remove_outliers(raw_data, span, delta)
    assert math.isnan(no_outliers["2021-01-01 00:10"]), "Outlier not removed!"


def test_remove_spike(raw_data, fbewma_data, mocker):
    # Setup
    span = 2
    low_clip = 2
    high_clip = 4
    delta = 2

    def clip_no_bugs(*args, **kwargs):
        return insert_raw_data_gaps(["2021-01-01 00:00", "2021-01-01 00:20"])

    def remove_outliers_no_bugs(*args, **kwargs):
        return insert_fbewma_data_gaps(
            ["2021-01-01 00:00", "2021-01-01 00:10", "2021-01-01 00:20"]
        )

    # I can use the same mocker here because clip wouldn't do anything to this data
    clip_mock = mocker.patch(
        "hydrobot.filters.clip",
        side_effect=clip_no_bugs,
    )

    remove_outlier_mock = mocker.patch(
        "hydrobot.filters.remove_outliers",
        side_effect=remove_outliers_no_bugs,
    )

    spike_removed = filters.remove_spikes(raw_data, span, high_clip, low_clip, delta)
    assert math.isnan(spike_removed["2021-01-01 00:10"]), "Spike not removed!"
