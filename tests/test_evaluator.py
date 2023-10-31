import math
from unittest.mock import call

import numpy as np
import pandas as pd
import pytest
import hydro_processing_tools.evaluator as evaluator

raw_data_dict = {
    "2021-01-01 00:00": 1.0,
    "2021-01-01 00:15": 2.0,
    "2021-01-01 00:30": 10.0,
    "2021-01-01 00:45": 4.0,
    "2021-01-01 01:00": 5.0,
}

gap_data_dict = {
    "2021-01-01 00:00": np.NaN,
    "2021-01-01 00:15": 2.0,
    "2021-01-01 00:30": np.NaN,
    "2021-01-01 00:45": np.NaN,
    "2021-01-01 01:00": 5.0,
    "2021-01-01 01:15": np.NaN,
    "2021-01-01 01:30": np.NaN,
    "2021-01-01 01:45": np.NaN,
    "2021-01-01 02:00": 0.0,
    "2021-01-01 02:15": 0.0,
    "2021-01-01 02:30": np.NaN,
    "2021-01-01 02:45": np.NaN,
}


@pytest.fixture
def raw_data():
    """Example data for testing. Do not change these values!"""
    # Allows parametrization with a list of keys to change to np.nan
    data_series = pd.Series(raw_data_dict)
    return data_series


@pytest.fixture
def gap_data():
    """Example data for testing. Do not change these values!"""
    # Allows parametrization with a list of keys to change to np.nan
    data_series = pd.Series(gap_data_dict)
    return data_series


@pytest.mark.dependency(name="test_gap_finder")
def test_gap_finder(raw_data, gap_data):
    no_gap_list = evaluator.gap_finder(raw_data)
    assert no_gap_list == [], "Gap found where there should be no gap"

    gap_list = evaluator.gap_finder(gap_data)
    assert len(gap_list) >= 4, "gap_finder did not find one or more of the gaps"
    assert len(gap_list) <= 4, "gap_finder found too many gaps"
    assert gap_list[0][1] == 1, "gap length of 1 not calculated correctly"
    assert gap_list[1][1] == 2, "gap length of 2 not calculated correctly"
    assert gap_list[2][1] == 3, "gap length of 3 not calculated correctly"


@pytest.mark.dependency(name="test_small_gap_closer")
def test_small_gap_closer(raw_data, gap_data):
    # No gaps here, nothing should happen
    no_gaps = evaluator.small_gap_closer(raw_data, 1)
    assert no_gaps.equals(raw_data), "Data without gaps should not be modified, but was"

    # All gaps should be closed
    removed_gaps = evaluator.small_gap_closer(gap_data, 5)
    assert len(removed_gaps) == 4, "Data changed during gap closing"

    # Should still have one gap of len 3, others closed
    some_gaps = evaluator.small_gap_closer(gap_data, 2)
    assert len(some_gaps) == 7, "gap_finder did not find one or more of the gaps"


@pytest.mark.dependency(depends=["test_gap_finder", "test_small_gap_closer"])
def test_small_gap_closer_part2(raw_data, gap_data):
    # All gaps should be closed
    removed_gaps = evaluator.small_gap_closer(gap_data, 5)
    assert evaluator.gap_finder(removed_gaps) == [], "Gap not closed!"

    # Should still have one gap of len 3, others closed
    some_gaps = evaluator.small_gap_closer(gap_data, 2)
    assert len(evaluator.gap_finder(some_gaps)) < 2, "Not enough gaps were removed"
    assert len(evaluator.gap_finder(some_gaps)) > 0, "Too many gaps were removed"
    assert (
        evaluator.gap_finder(some_gaps)[0][1] == 3
    ), "incorrect gap length after gap closure"
