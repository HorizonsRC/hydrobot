"""Test the filters module."""

import numpy as np
import pandas as pd
import pytest

import hydrobot.utils as utils

mowsecs_data_dict = {
    "2619302400": 42,
    "2619302700": 42,
    "2619303000": 42,
    "2619303300": 42,
    "2619303600": 42,
    "2619303900": 42,
    "2619304200": 42,
    "2619304500": 42,
    "2619304800": 42,
    "2619305100": 42,
}

datetime_data_dict = {
    "2023-01-01 00:00:00": 42,
    "2023-01-01 00:05:00": 42,
    "2023-01-01 00:10:00": 42,
    "2023-01-01 00:15:00": 42,
    "2023-01-01 00:20:00": 42,
    "2023-01-01 00:25:00": 42,
    "2023-01-01 00:30:00": 42,
    "2023-01-01 00:35:00": 42,
    "2023-01-01 00:40:00": 42,
    "2023-01-01 00:45:00": 42,
}


@pytest.fixture()
def mowsecs_data():
    """Get example data for testing.

    Do not change these values!
    """
    # Allows parametrization with a list of keys to change to np.nan
    return pd.Series(mowsecs_data_dict)


@pytest.fixture()
def datetime_data():
    """Get example data for testing.

    Do not change these values!
    """
    # Allows parametrization with a list of keys to change to np.nan
    data = pd.Series(datetime_data_dict)
    data.index = pd.to_datetime(data.index)
    return data


def test_mowsecs_to_timestamp(mowsecs_data, datetime_data):
    """Test mowsecs_to_datetime_index utility."""
    for mowsec, timestamp in zip(mowsecs_data.index.values, datetime_data.index.values):
        ms_to_dt = utils.mowsecs_to_timestamp(mowsec)
        assert ms_to_dt == timestamp

        str_ms_to_dt = utils.mowsecs_to_timestamp(str(mowsec))
        assert str_ms_to_dt == timestamp

        float_ms_to_dt = utils.mowsecs_to_timestamp(float(mowsec))
        assert float_ms_to_dt == timestamp


def test_timestamp_to_mowsecs(mowsecs_data, datetime_data):
    """Test mowsecs_to_datetime_index utility."""
    for timestamp, mowsec in zip(datetime_data.index.values, mowsecs_data.index.values):
        dt_to_ms = utils.timestamp_to_mowsecs(timestamp)

        assert dt_to_ms == int(mowsec)


def test_mowsecs_to_datetime_index(mowsecs_data, datetime_data):
    """Test mowsecs_to_datetime_index utility."""
    ms_to_dt = utils.mowsecs_to_datetime_index(mowsecs_data.index)

    assert ms_to_dt.equals(datetime_data.index)


def test_datetime_index_to_mowsecs(mowsecs_data, datetime_data):
    """Test mowsecs_to_datetime_index utility."""
    dt_to_ms = utils.datetime_index_to_mowsecs(datetime_data.index)

    assert dt_to_ms.equals(mowsecs_data.index.astype(np.int64))
