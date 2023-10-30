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
    "2021-01-01 00:45": pd.NA,
    "2021-01-01 01:00": 5.0,
    "2021-01-01 01:15": pd.NA,
    "2021-01-01 01:30": pd.NA,
    "2021-01-01 01:45": np.NaN,
    "2021-01-01 01:00": 0.0,
    "2021-01-01 01:15": 0.0,
    "2021-01-01 01:30": pd.NA,
    "2021-01-01 01:45": pd.NA,
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


def test_gap_finder(raw_data, gap_data):
    no_gap_list = evaluator.gap_finder(raw_data)
    assert no_gap_list == [], "Gap found where there should be no gap"

    gap_list = evaluator.gap_finder(gap_data)
    assert len(gap_list) >= 4, "gap_finder did not find one or more of the gaps"
    assert len(gap_list) <= 4, "gap_finder found too many gaps"
    assert gap_list[0][1] == 1, "gap length of 1 not calculated correctly"
    assert gap_list[1][1] == 2, "gap length of 2 not calculated correctly"
    assert gap_list[2][1] == 3, "gap length of 3 not calculated correctly"
