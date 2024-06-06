"""Test the filters module."""

import warnings

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
    for mowsec, timestamp in zip(
        mowsecs_data.index.values, datetime_data.index.values, strict=True
    ):
        ms_to_dt = utils.mowsecs_to_timestamp(mowsec)
        assert ms_to_dt == timestamp

        str_ms_to_dt = utils.mowsecs_to_timestamp(str(mowsec))
        assert str_ms_to_dt == timestamp

        float_ms_to_dt = utils.mowsecs_to_timestamp(float(mowsec))
        assert float_ms_to_dt == timestamp


def test_timestamp_to_mowsecs(mowsecs_data, datetime_data):
    """Test mowsecs_to_datetime_index utility."""
    for timestamp, mowsec in zip(
        datetime_data.index.values, mowsecs_data.index.values, strict=True
    ):
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


def test_compare_two_qc_take_min():
    """Test compare_two_qc_take_min utility."""
    a = pd.Series(
        {
            "2021-01-01 01:00": 5,
            "2021-01-01 03:00": 6,
            "2021-01-01 09:00": 5,
        }
    )
    b = pd.Series(
        {
            "2021-01-01 01:00": 6,
            "2021-01-01 02:00": 4,
            "2021-01-01 05:00": 5,
            "2021-01-01 06:00": 6,
        }
    )
    c = pd.Series(
        {
            "2021-01-01 01:00": 5,
            "2021-01-01 02:00": 4,
            "2021-01-01 05:00": 5,
            "2021-01-01 06:00": 6,
            "2021-01-01 09:00": 5,
        }
    )

    assert utils.compare_two_qc_take_min(a, b).equals(c), "1"
    assert utils.compare_qc_list_take_min([a, b, c]).equals(c), "2"

    d = pd.Series(
        {
            "2021-01-01 01:00": 5,
            "2021-01-01 03:00": 6,
            "2021-01-01 09:00": 5,
        }
    )
    e = pd.Series(
        {
            "2021-01-01 01:30": 6,
            "2021-01-01 02:00": 4,
            "2021-01-01 05:00": 5,
            "2021-01-01 06:00": 6,
        }
    )

    print(utils.compare_two_qc_take_min(d, e))

    assert utils.compare_two_qc_take_min(d, e).equals(
        c
    ), "unequal start times breaks it"

    f = pd.Series(
        {
            "2021-01-01 01:30": 5,
            "2021-01-01 03:00": 6,
            "2021-01-01 09:00": 5,
        }
    )
    g = pd.Series(
        {
            "2021-01-01 01:00": 6,
            "2021-01-01 02:00": 4,
            "2021-01-01 05:00": 5,
            "2021-01-01 06:00": 6,
        }
    )
    h = pd.Series(
        {
            "2021-01-01 01:00": 6,
            "2021-01-01 01:30": 5,
            "2021-01-01 02:00": 4,
            "2021-01-01 05:00": 5,
            "2021-01-01 06:00": 6,
            "2021-01-01 09:00": 5,
        }
    )

    assert utils.compare_two_qc_take_min(f, g).equals(
        h
    ), "unequal start times aren't accounted for"


def test_series_rounder():
    """Test series_rounder()."""
    a = pd.Series(
        {
            "2021-01-01 01:03": 5,
            "2021-01-01 01:09": 4,
            "2021-01-01 01:15": 5,
            "2021-01-01 01:21": 6,
            "2021-01-01 01:27": 5,
            "2021-01-01 01:33": 5,
            "2021-01-01 01:39": 4,
            "2021-01-01 01:45": 5,
            "2021-01-01 01:51": 6,
            "2021-01-01 01:57": 5,
        }
    )
    a_copy = a.copy()

    b = pd.Series(
        {
            "2021-01-01 01:06": 5,
            "2021-01-01 01:12": 4,
            "2021-01-01 01:18": 5,
            "2021-01-01 01:24": 6,
            "2021-01-01 01:30": 5,
            "2021-01-01 01:36": 5,
            "2021-01-01 01:42": 4,
            "2021-01-01 01:48": 5,
            "2021-01-01 01:54": 6,
            "2021-01-01 02:00": 5,
        }
    )
    b.index = pd.DatetimeIndex(b.index)

    with warnings.catch_warnings(record=True) as w:
        c = utils.series_rounder(a, "6min")
        assert len(w) == 1
        assert "INPUT_WARNING" in str(w[0].message)

    assert c.equals(b), "Function doesn't work"
    assert a.equals(a_copy), "Original modified"


def test_rainfall_six_minute_repacker():
    """Test rainfall_six_minute_repacker."""
    series = pd.Series(
        {
            "2021-01-01 01:57": 100,
        }
    )
    original = series.copy()

    with warnings.catch_warnings(record=True) as w:
        repacked = utils.rainfall_six_minute_repacker(series)
        assert len(w) == 1, "Incorrect number of warnings"
        assert "INPUT_WARNING" in str(w[0].message), "Wrong kind of warning"
    assert original.equals(series), "Original modified"

    expected = pd.Series(
        {
            "2021-01-01 01:54": 50,
            "2021-01-01 02:00": 50,
        }
    )
    expected.index = pd.DatetimeIndex(expected.index)
    assert expected.equals(repacked), "First case broken"

    ###########################################################################
    series = pd.Series(
        {
            "2021-01-01 01:56": 100,
        }
    )
    series.index = pd.DatetimeIndex(series.index)

    repacked = utils.rainfall_six_minute_repacker(series)
    expected = pd.Series(
        {
            "2021-01-01 01:54": 67,
            "2021-01-01 02:00": 33,
        }
    )
    expected.index = pd.DatetimeIndex(expected.index)

    assert expected.equals(repacked), "Rounding broken"

    ###########################################################################
    series = pd.Series(
        {
            "2021-01-01 01:54": 0,
            "2021-01-01 01:56": 100,
        }
    )
    series.index = pd.DatetimeIndex(series.index)

    repacked = utils.rainfall_six_minute_repacker(series)
    expected = pd.Series(
        {
            "2021-01-01 01:54": 0,
            "2021-01-01 02:00": 100,
        }
    )
    expected.index = pd.DatetimeIndex(expected.index)

    assert expected.equals(repacked), "Second case broken"

    ###########################################################################
    series = pd.Series(
        {
            "2021-01-01 01:53": 0,
            "2021-01-01 01:57": 100,
        }
    )
    series.index = pd.DatetimeIndex(series.index)

    repacked = utils.rainfall_six_minute_repacker(series)
    expected = pd.Series(
        {
            "2021-01-01 01:48": 0,
            "2021-01-01 01:54": 25,
            "2021-01-01 02:00": 75,
        }
    )
    expected.index = pd.DatetimeIndex(expected.index)

    assert expected.equals(repacked), "Third case broken"

    ###########################################################################
    series = pd.Series(
        {
            "2021-01-01 01:50": 100,
            "2021-01-01 01:58": 100,
        }
    )
    series.index = pd.DatetimeIndex(series.index)

    repacked = utils.rainfall_six_minute_repacker(series)
    expected = pd.Series(
        {
            "2021-01-01 01:48": 67,
            "2021-01-01 01:54": 66,
            "2021-01-01 02:00": 67,
        }
    )
    expected.index = pd.DatetimeIndex(expected.index)

    assert expected.equals(repacked), "Summing/rounding broken"


def test_check_data_ramp_and_quality():
    """Test check_data_ramp()."""
    start_std = pd.Series(
        {
            "2021-01-01 01:00": 0,
            "2021-01-01 01:05": 100,
            "2021-01-01 01:10": 100,
        }
    )
    start_std.index = pd.DatetimeIndex(start_std.index)
    start_check = pd.Series(
        {
            "2021-01-01 01:00": 0,
            "2021-01-01 01:10": 300,
        }
    )
    start_check.index = pd.DatetimeIndex(start_check.index)

    original_std = start_std.copy()
    original_check = start_check.copy()

    expected_std = pd.Series(
        {
            "2021-01-01 01:00": 0,
            "2021-01-01 01:05": 150,
            "2021-01-01 01:10": 150,
        }
    )
    expected_std.index = pd.DatetimeIndex(expected_std.index)
    expected_std = expected_std.astype(np.float64)
    expected_quality = pd.Series(
        {
            "2021-01-01 01:00": 400,
            "2021-01-01 01:10": 0,
        }
    )
    expected_quality.index = pd.DatetimeIndex(expected_quality.index)

    actual_std, actual_quality = utils.check_data_ramp_and_quality(
        start_std, start_check
    )

    assert start_std.equals(original_std), "original std modified"
    assert start_check.equals(original_check), "original check modified"

    assert np.allclose(
        actual_std, expected_std, rtol=1e-05, atol=1e-08, equal_nan=False
    ), "Standard data incorrect after single check"
    assert np.allclose(
        actual_quality, expected_quality, rtol=1e-05, atol=1e-08, equal_nan=False
    ), "Quality data incorrect after single check"

    ###########################################################################

    start_std = pd.Series(
        {
            "2021-01-01 01:00:00": 0,
            "2021-01-01 01:00:01": 100,
            "2021-01-01 01:00:02": 100,
            "2021-01-01 01:00:03": 100,
            "2021-01-01 01:00:04": 100,
            "2021-01-01 01:00:05": 100,
            "2021-01-01 01:01:06": 100,
            "2021-01-01 01:01:07": 100,
            "2021-01-01 01:03:08": 100,
            "2021-01-01 01:04:09": 100,
            "2021-01-01 01:04:10": 100,
            "2021-01-01 01:05": 100,
        }
    )
    start_std.index = pd.DatetimeIndex(start_std.index)
    start_check = pd.Series(
        {
            "2021-01-01 01:00": 0,
            "2021-01-01 01:00:04": 460,
            "2021-01-01 01:05": 735,
        }
    )
    start_check.index = pd.DatetimeIndex(start_check.index)

    original_std = start_std.copy()
    original_check = start_check.copy()

    expected_std = pd.Series(
        {
            "2021-01-01 01:00:00": 0,
            "2021-01-01 01:00:01": 115,
            "2021-01-01 01:00:02": 115,
            "2021-01-01 01:00:03": 115,
            "2021-01-01 01:00:04": 115,
            "2021-01-01 01:00:05": 105,
            "2021-01-01 01:01:06": 105,
            "2021-01-01 01:01:07": 105,
            "2021-01-01 01:03:08": 105,
            "2021-01-01 01:04:09": 105,
            "2021-01-01 01:04:10": 105,
            "2021-01-01 01:05": 105,
        }
    )
    expected_std.index = pd.DatetimeIndex(expected_std.index)
    expected_std = expected_std.astype(np.float64)
    expected_quality = pd.Series(
        {
            "2021-01-01 01:00": 400,
            "2021-01-01 01:00:04": 600,
            "2021-01-01 01:05": 0,
        }
    )
    expected_quality.index = pd.DatetimeIndex(expected_quality.index)

    actual_std, actual_quality = utils.check_data_ramp_and_quality(
        start_std, start_check
    )

    assert start_std.equals(original_std), "original std modified 2"
    assert start_check.equals(original_check), "original check modified 2"

    assert np.allclose(
        actual_std, expected_std, rtol=1e-05, atol=1e-08, equal_nan=False
    ), "Standard data incorrect after double check + different time scales"
    assert np.allclose(
        actual_quality, expected_quality, rtol=1e-05, atol=1e-08, equal_nan=False
    ), "Quality data incorrect after double check + different time scales"

    ###########################################################################

    start_std = pd.Series(
        {
            "2021-01-01 01:00:01": 0,
            "2021-01-01 01:00:02": 100,
            "2021-01-01 01:00:03": 100,
            "2021-01-01 01:00:05": 100,
            "2021-01-01 01:01:06": 100,
            "2021-01-01 01:01:07": 100,
            "2021-01-01 01:03:08": 100,
            "2021-01-01 01:04:09": 100,
            "2021-01-01 01:04:10": 100,
            "2021-01-01 01:05": 100,
        }
    )
    start_std.index = pd.DatetimeIndex(start_std.index)
    start_check1 = pd.Series(
        {
            "2021-01-01 01:00": 0,
            "2021-01-01 01:00:05": 460,
            "2021-01-01 01:05": 735,
        }
    )
    start_check1.index = pd.DatetimeIndex(start_check1.index)
    start_check2 = pd.Series(
        {
            "2021-01-01 01:00:01": 0,
            "2021-01-01 01:00:04": 460,
            "2021-01-01 01:05": 735,
        }
    )
    start_check2.index = pd.DatetimeIndex(start_check2.index)
    start_check3 = pd.Series(
        {
            "2021-01-01 01:00:01": 0,
            "2021-01-01 01:00:05": 460,
            "2021-01-01 01:04:59": 735,
        }
    )
    start_check3.index = pd.DatetimeIndex(start_check3.index)

    with pytest.raises(KeyError):
        (
            utils.check_data_ramp_and_quality(start_std, start_check1),
            "First check missing breaks it",
        )
    with pytest.raises(KeyError):
        (
            utils.check_data_ramp_and_quality(start_std, start_check2),
            "Middle check missing breaks it",
        )
    with pytest.raises(KeyError):
        (
            utils.check_data_ramp_and_quality(start_std, start_check3),
            "Last check missing breaks it",
        )


def test_add_empty_rainfall_to_std():
    """Testing add_empty_rainfall_to_std()."""
    start_std = pd.Series(
        {
            "2021-01-01 01:00:01": 0,
            "2021-01-01 01:00:02": 100,
            "2021-01-01 01:00:03": 100,
            "2021-01-01 01:00:05": 100,
            "2021-01-01 01:01:06": 100,
            "2021-01-01 01:01:07": 100,
            "2021-01-01 01:03:08": 100,
            "2021-01-01 01:04:09": 100,
            "2021-01-01 01:04:10": 100,
            "2021-01-01 01:05": 100,
        }
    )
    start_std.index = pd.DatetimeIndex(start_std.index)
    original_std = start_std.copy()

    start_check1 = pd.Series(
        {
            "2021-01-01 01:00:01": 0,
            "2021-01-01 01:00:05": 460,
            "2021-01-01 01:05": 735,
        }
    )
    start_check1.index = pd.DatetimeIndex(start_check1.index)
    original_check1 = start_check1.copy()
    expected_std1 = pd.Series(
        {
            "2021-01-01 01:00:01": 0,
            "2021-01-01 01:00:02": 100,
            "2021-01-01 01:00:03": 100,
            "2021-01-01 01:00:05": 100,
            "2021-01-01 01:01:06": 100,
            "2021-01-01 01:01:07": 100,
            "2021-01-01 01:03:08": 100,
            "2021-01-01 01:04:09": 100,
            "2021-01-01 01:04:10": 100,
            "2021-01-01 01:05": 100,
        }
    )
    expected_std1.index = pd.DatetimeIndex(expected_std1.index)

    start_check2 = pd.Series(
        {
            "2021-01-01 01:00": 0,
            "2021-01-01 01:00:05": 460,
            "2021-01-01 01:04:59": 735,
        }
    )
    start_check2.index = pd.DatetimeIndex(start_check2.index)
    original_check2 = start_check2.copy()
    expected_std2 = pd.Series(
        {
            "2021-01-01 01:00": 0,
            "2021-01-01 01:00:01": 0,
            "2021-01-01 01:00:02": 100,
            "2021-01-01 01:00:03": 100,
            "2021-01-01 01:00:05": 100,
            "2021-01-01 01:01:06": 100,
            "2021-01-01 01:01:07": 100,
            "2021-01-01 01:03:08": 100,
            "2021-01-01 01:04:09": 100,
            "2021-01-01 01:04:10": 100,
            "2021-01-01 01:04:59": 0,
            "2021-01-01 01:05": 100,
        }
    )
    expected_std2.index = pd.DatetimeIndex(expected_std2.index)

    start_check3 = pd.Series(
        {
            "2021-01-01 01:00": 0,
            "2021-01-01 01:00:04": 460,
            "2021-01-01 01:05:01": 735,
        }
    )
    start_check3.index = pd.DatetimeIndex(start_check3.index)
    original_check3 = start_check3.copy()
    expected_std3 = pd.Series(
        {
            "2021-01-01 01:00": 0,
            "2021-01-01 01:00:01": 0,
            "2021-01-01 01:00:02": 100,
            "2021-01-01 01:00:03": 100,
            "2021-01-01 01:00:04": 0,
            "2021-01-01 01:00:05": 100,
            "2021-01-01 01:01:06": 100,
            "2021-01-01 01:01:07": 100,
            "2021-01-01 01:03:08": 100,
            "2021-01-01 01:04:09": 100,
            "2021-01-01 01:04:10": 100,
            "2021-01-01 01:05": 100,
            "2021-01-01 01:05:01": 0,
        }
    )
    expected_std3.index = pd.DatetimeIndex(expected_std3.index)

    actual_std1 = utils.add_empty_rainfall_to_std(start_std, start_check1)
    actual_std2 = utils.add_empty_rainfall_to_std(start_std, start_check2)
    actual_std3 = utils.add_empty_rainfall_to_std(start_std, start_check3)

    assert start_std.equals(original_std), "standard data modified, side effect"
    assert start_check1.equals(original_check1), "check data 1 modified, side effect"
    assert start_check2.equals(original_check2), "check data 2 modified, side effect"
    assert start_check3.equals(original_check3), "check data 3 modified, side effect"

    assert expected_std1.equals(actual_std1), "Data wrong when check is a subset of std"
    assert expected_std2.equals(actual_std2), "Data wrong when check intersects std"
    assert expected_std3.equals(
        actual_std3
    ), "Data wrong when check does not intersect std"
