import hydrobot.data_sources as data_sources
import hydrobot.evaluator as evaluator
import numpy as np
import pandas as pd
import pytest
import warnings
from annalist.annalist import Annalist

import hydrobot.data_sources as data_sources
import hydrobot.evaluator as evaluator

ann = Annalist()
ann.configure()

raw_data_dict = {
    pd.Timestamp("2021-01-01 00:00"): 1.0,
    pd.Timestamp("2021-01-01 00:15"): 2.0,
    pd.Timestamp("2021-01-01 00:30"): 10.0,
    pd.Timestamp("2021-01-01 00:45"): 4.0,
    pd.Timestamp("2021-01-01 01:00"): 5.0,
}

gap_data_dict = {
    pd.Timestamp("2021-01-01 00:00"): np.NaN,
    pd.Timestamp("2021-01-01 00:15"): 2.0,
    pd.Timestamp("2021-01-01 00:30"): np.NaN,
    pd.Timestamp("2021-01-01 00:45"): np.NaN,
    pd.Timestamp("2021-01-01 01:00"): 5.0,
    pd.Timestamp("2021-01-01 01:15"): np.NaN,
    pd.Timestamp("2021-01-01 01:30"): np.NaN,
    pd.Timestamp("2021-01-01 01:45"): np.NaN,
    pd.Timestamp("2021-01-01 02:00"): 0.0,
    pd.Timestamp("2021-01-01 02:15"): 0.0,
    pd.Timestamp("2021-01-01 02:30"): np.NaN,
    pd.Timestamp("2021-01-01 02:45"): np.NaN,
}

check_data_dict = {
    pd.Timestamp("2021-01-01 00:15"): 2.1,
    pd.Timestamp("2021-01-01 00:45"): 7.0,
    pd.Timestamp("2021-01-01 01:00"): 25.0,
}

qc_data_dict = {
    pd.Timestamp("2021-01-01 00:00"): 600,
    pd.Timestamp("2021-01-01 00:15"): 500,
    pd.Timestamp("2021-01-01 00:45"): 600,
    pd.Timestamp("2021-01-01 01:00"): 500,
    pd.Timestamp("2021-01-01 01:30"): 500,
    pd.Timestamp("2021-01-01 02:15"): 600,
    pd.Timestamp("2021-01-01 02:45"): 600,
}


@pytest.fixture
def raw_data():
    """Example data for testing. Do not change these values!"""
    data_series = pd.Series(raw_data_dict)
    return data_series


@pytest.fixture
def gap_data():
    """Example data for testing. Do not change these values!"""
    data_series = pd.Series(gap_data_dict)
    return data_series


@pytest.fixture
def check_data():
    """Example data for testing. Do not change these values!"""
    data_series = pd.Series(check_data_dict)
    return data_series


@pytest.fixture
def qc_data():
    """Example data for testing. Do not change these values!"""
    data_series = pd.Series(qc_data_dict)
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


def test_find_nearest_time(gap_data):
    assert evaluator.find_nearest_time(
        gap_data, pd.Timestamp("2021-01-01 01:00")
    ) == pd.Timestamp("2021-01-01 01:00"), "does not find exact value"
    assert evaluator.find_nearest_time(
        gap_data, pd.Timestamp("2021-01-01 01:07")
    ) == pd.Timestamp("2021-01-01 01:00"), "does not round down correctly"
    assert evaluator.find_nearest_time(
        gap_data, pd.Timestamp("2021-01-01 01:08")
    ) == pd.Timestamp(
        "2021-01-01 01:15"
    ), "does not round up or does not round up to null correctly"
    assert evaluator.find_nearest_time(
        gap_data, pd.Timestamp("2021-01-01 01:23")
    ) == pd.Timestamp("2021-01-01 01:30"), "middle of nulls not reading correctly"
    assert evaluator.find_nearest_time(
        gap_data, pd.Timestamp("2021-01-01 00:00")
    ) == pd.Timestamp("2021-01-01 00:00"), "start time not accepted"
    assert evaluator.find_nearest_time(
        gap_data, pd.Timestamp("2021-01-01 02:45")
    ) == pd.Timestamp("2021-01-01 02:45"), "end time not accepted"
    with pytest.raises(Exception):
        # out of range forwards
        evaluator.find_nearest_time(gap_data, pd.Timestamp("2021-01-01 02:46"))
    with pytest.raises(Exception):
        # out of range backwards
        evaluator.find_nearest_time(gap_data, pd.Timestamp("2020-12-31 23:59"))


def test_find_nearest_valid_time(gap_data, qc_data):
    assert evaluator.find_nearest_valid_time(
        qc_data, pd.Timestamp("2021-01-01 01:00")
    ) == pd.Timestamp("2021-01-01 01:00"), "does not find exact value"
    assert evaluator.find_nearest_valid_time(
        qc_data, pd.Timestamp("2021-01-01 01:07")
    ) == pd.Timestamp("2021-01-01 01:00"), "does not round down correctly"
    assert evaluator.find_nearest_valid_time(
        qc_data, pd.Timestamp("2021-01-01 01:08")
    ) == pd.Timestamp(
        "2021-01-01 01:00"
    ), "does not round down when round up would lead to null"
    assert evaluator.find_nearest_valid_time(
        gap_data, pd.Timestamp("2021-01-01 01:23")
    ) == pd.Timestamp("2021-01-01 01:00"), "middle of nulls not reading correctly"
    assert evaluator.find_nearest_valid_time(
        qc_data, pd.Timestamp("2021-01-01 00:00")
    ) == pd.Timestamp("2021-01-01 00:00"), "start time not accepted"
    assert evaluator.find_nearest_valid_time(
        qc_data, pd.Timestamp("2021-01-01 02:45")
    ) == pd.Timestamp("2021-01-01 02:45"), "end time not accepted"
    with pytest.raises(Exception):
        # out of range forwards
        evaluator.find_nearest_valid_time(gap_data, pd.Timestamp("2021-01-01 02:46"))
    with pytest.raises(Exception):
        # out of range backwards
        evaluator.find_nearest_valid_time(gap_data, pd.Timestamp("2020-12-31 23:59"))


def test_check_data_quality_code(raw_data, check_data):
    meas = data_sources.Measurement(10, 2.0)
    with pytest.warns(Warning):
        assert (
            len(evaluator.check_data_quality_code(raw_data, pd.Series({}), meas)) == 1
        ), "fails for empty check data series"
    output = evaluator.check_data_quality_code(raw_data, check_data, meas)
    assert (
        len(output) == len(check_data) + 1
    ), "different amount of QC values than check data values"
    assert output.iloc[0] == 600, "QC 600 test failed"
    assert output.iloc[1] == 500, "QC 500 test failed"
    assert output.iloc[2] == 400, "QC 400 test failed"
    assert output.iloc[3] == 0, "Should have QC 0 at the end"


def test_base_data_qc_filter(gap_data, qc_data):
    assert len(
        evaluator.base_data_qc_filter(
            gap_data, pd.Series({pd.Timestamp("2021-01-01 00:00"): True})
        )
    ) == len(gap_data), "True filter removed data"
    assert (
        len(
            evaluator.base_data_qc_filter(
                gap_data, pd.Series({pd.Timestamp("2021-01-01 00:00"): False})
            )
        )
        == 0
    ), "False filter did not delete all data"
    data_600 = evaluator.base_data_qc_filter(gap_data, qc_data == 600)
    assert pd.Timestamp("2021-01-01 00:00") in data_600
    assert pd.Timestamp("2021-01-01 00:15") not in data_600
    assert pd.Timestamp("2021-01-01 00:30") not in data_600
    assert pd.Timestamp("2021-01-01 00:45") in data_600
    assert pd.Timestamp("2021-01-01 01:00") not in data_600
    assert pd.Timestamp("2021-01-01 01:15") not in data_600
    assert pd.Timestamp("2021-01-01 02:30") in data_600
    assert pd.Timestamp("2021-01-01 02:45") in data_600

    data_500 = evaluator.base_data_qc_filter(gap_data, qc_data == 500)
    assert pd.Timestamp("2021-01-01 00:00") not in data_500
    assert pd.Timestamp("2021-01-01 00:15") in data_500
    assert pd.Timestamp("2021-01-01 00:30") in data_500
    assert pd.Timestamp("2021-01-01 00:45") not in data_500
    assert pd.Timestamp("2021-01-01 01:00") in data_500
    assert pd.Timestamp("2021-01-01 01:15") in data_500
    assert pd.Timestamp("2021-01-01 02:30") not in data_500
    assert pd.Timestamp("2021-01-01 02:45") not in data_500


def test_base_data_meets_qc(gap_data, qc_data):
    assert len(
        evaluator.base_data_meets_qc(
            gap_data, pd.Series({pd.Timestamp("2021-01-01 00:00"): 600}), 600
        )
    ) == len(gap_data), "True filter removed data"
    assert (
        len(
            evaluator.base_data_meets_qc(
                gap_data, pd.Series({pd.Timestamp("2021-01-01 00:00"): 500}), 600
            )
        )
        == 0
    ), "False filter did not delete all data"
    data_600 = evaluator.base_data_meets_qc(gap_data, qc_data, 600)
    assert pd.Timestamp("2021-01-01 00:00") in data_600
    assert pd.Timestamp("2021-01-01 00:15") not in data_600
    assert pd.Timestamp("2021-01-01 00:30") not in data_600
    assert pd.Timestamp("2021-01-01 00:45") in data_600
    assert pd.Timestamp("2021-01-01 01:00") not in data_600
    assert pd.Timestamp("2021-01-01 01:15") not in data_600
    assert pd.Timestamp("2021-01-01 02:30") in data_600
    assert pd.Timestamp("2021-01-01 02:45") in data_600

    data_500 = evaluator.base_data_meets_qc(gap_data, qc_data, 500)
    assert pd.Timestamp("2021-01-01 00:00") not in data_500
    assert pd.Timestamp("2021-01-01 00:15") in data_500
    assert pd.Timestamp("2021-01-01 00:30") in data_500
    assert pd.Timestamp("2021-01-01 00:45") not in data_500
    assert pd.Timestamp("2021-01-01 01:00") in data_500
    assert pd.Timestamp("2021-01-01 01:15") in data_500
    assert pd.Timestamp("2021-01-01 02:30") not in data_500
    assert pd.Timestamp("2021-01-01 02:45") not in data_500


def test_missing_data_quality_code(gap_data, qc_data):
    no_gap_qc = evaluator.missing_data_quality_code(
        gap_data.fillna(3), qc_data, gap_limit=0
    )
    assert no_gap_qc.equals(qc_data), "QC data modified when there are no gaps"

    new_qc = evaluator.missing_data_quality_code(gap_data, qc_data, gap_limit=0)
    assert new_qc[pd.Timestamp("2021-01-01 00:00")] == 100, "Starting gap not added"
    assert new_qc[pd.Timestamp("2021-01-01 00:15")] == 500, "Starting gap not closed"
    assert new_qc[pd.Timestamp("2021-01-01 02:30")] == 100, "Ending gap not added"
    with pytest.raises(Exception):
        # Mid-gap QC not replaced
        new_qc[pd.Timestamp("2021-01-01 01:30")]
    assert new_qc[pd.Timestamp("2021-01-01 02:00")] == 500, "Gap in middle not closed"
