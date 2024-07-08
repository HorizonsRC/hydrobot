"""Test rainfall specific utils."""

import pandas as pd
import pytest

import hydrobot.measurement_specific_functions.rainfall as rf


def test_rainfall_time_since_inspection_points():
    """Test rainfall_time_since_inspection_points()."""
    start_check = pd.Series(
        {
            "2021-01-01 01:00": 0,
            "2021-02-02 01:05": 100,
            "2021-05-03 01:10": 100,
            "2022-05-04 01:10": 100,
            "2024-05-05 01:10": 100,
        }
    )
    start_check.index = pd.DatetimeIndex(start_check.index)

    original_check = start_check.copy()

    expected_points = pd.Series(
        {
            "2021-01-01 01:00": 0,
            "2021-02-02 01:05": 1,
            "2021-05-03 01:10": 3,
            "2022-05-04 01:10": 12,
            "2024-05-05 01:10": -1000,
        }
    )
    expected_points.index = pd.DatetimeIndex(expected_points.index)

    actual_points = rf.rainfall_time_since_inspection_points(start_check)

    assert start_check.equals(original_check), "original check modified"
    assert actual_points.equals(expected_points), "One of them failed"

    with pytest.raises(ValueError, match="Cannot have empty rainfall check series"):
        rf.rainfall_time_since_inspection_points(pd.Series({}))


def test_points_combiner():
    """Test points_combiner()."""
    a = pd.Series(
        {
            "2021-01-01 01:00": 0,
            "2021-01-01 01:01": 1,
            "2021-01-01 01:03": 0,
            "2021-01-01 01:04": 1,
            "2021-01-01 01:06": 2,
            "2021-01-01 01:08": 0,
        }
    )
    a.index = pd.DatetimeIndex(a.index)

    b = pd.Series(
        {
            "2021-01-01 01:00": 0,
            "2021-01-01 01:02": 1,
            "2021-01-01 01:04": 0,
            "2021-01-01 01:06": 1,
            "2021-01-01 01:07": 0,
        }
    )
    b.index = pd.DatetimeIndex(b.index)

    c = pd.Series(
        {
            "2021-01-01 01:00": 0,
            "2021-01-01 01:05": 1,
        }
    )
    c.index = pd.DatetimeIndex(c.index)

    expected = pd.Series(
        {
            "2021-01-01 01:00": 0,
            "2021-01-01 01:01": 1,
            "2021-01-01 01:02": 2,
            "2021-01-01 01:03": 1,
            "2021-01-01 01:05": 2,
            "2021-01-01 01:06": 4,
            "2021-01-01 01:07": 3,
            "2021-01-01 01:08": 1,
        }
    )
    expected.index = pd.DatetimeIndex(expected.index)

    orig_a = a.copy()
    orig_b = b.copy()
    orig_c = c.copy()

    actual = rf.points_combiner([a, b, c])

    assert a.equals(orig_a), "Original a changed"
    assert b.equals(orig_b), "Original b changed"
    assert c.equals(orig_c), "Original c changed"

    assert actual.equals(expected), "First test case doesn't work"

    ###########################################################################
    d = pd.Series({})

    actual2 = rf.points_combiner([a, b, c, d])
    assert actual2.equals(expected), "Empty series not filtered"

    ###########################################################################
    e = pd.Series(
        {
            "2021-01-01 01:02": 1,
            "2021-01-01 01:04": 0,
            "2021-01-01 01:06": 1,
            "2021-01-01 01:07": 0,
        }
    )
    e.index = pd.DatetimeIndex(e.index)
    orig_e = e.copy()

    actual3 = rf.points_combiner([a, e, c])
    assert e.equals(orig_e), "Original e changed"
    assert actual3.equals(expected), "Uneven starting values cause problems"

    ###########################################################################
    actual4 = rf.points_combiner([a])
    assert actual4.equals(a)

    ###########################################################################
    with pytest.raises(ValueError, match="At least one series must not be empty."):
        rf.points_combiner([])
    with pytest.raises(ValueError, match="At least one series must not be empty."):
        rf.points_combiner([d])
