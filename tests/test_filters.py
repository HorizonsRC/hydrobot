"""Test the filters module."""

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

constant_data_dict = {
    "2021-01-01 00:00": 1.9,
    "2021-01-01 00:05": 3.0,
    "2021-01-01 00:10": 3.0,
    "2021-01-01 00:15": 3.0,
    "2021-01-01 00:20": 3.00001,
    "2021-01-01 00:25": 3.001,
    "2021-01-01 00:30": 3.1,
    "2021-01-01 00:35": 6.1,
    "2021-01-01 00:40": 6.1,
    "2021-01-01 00:45": 6.1,
    "2021-01-01 00:50": 6.1,
    "2021-01-01 00:55": 6.1,
    "2021-01-01 01:00": 6.2,
}


@pytest.fixture()
def raw_data():
    """Get example data for testing.

    Do not change these values!
    """
    # Allows parametrization with a list of keys to change to np.nan
    return pd.Series(raw_data_dict)


def insert_raw_data_gaps(gaps):
    """Insert raw data gaps."""
    gap_data_dict = dict(raw_data_dict)
    for gap in gaps:
        gap_data_dict[gap] = np.nan
    data_series = pd.Series(gap_data_dict)
    return data_series


@pytest.fixture()
def fbewma_data():
    """Mock function returning correct values for fbewma.

    Running on one_outlier_data with span=4
    """
    return pd.Series(fbewma_data_dict)


@pytest.fixture()
def constant_data():
    """Mock function returning correct values for fbewma.

    Running on one_outlier_data with span=4
    """
    return pd.Series(constant_data_dict)


def insert_fbewma_data_gaps(gaps):
    """Insert FBEWMA data gaps."""
    for gap in gaps:
        fbewma_data_dict[gap] = np.nan
    return pd.Series(fbewma_data_dict)


# Actual tests begin here:
##########################


def test_clip(raw_data):
    """Test the clip function."""
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

    assert not math.isnan(raw_data["2021-01-01 00:00"]), "Original low value changed!"
    assert not math.isnan(raw_data["2021-01-01 00:20"]), "Original high value changed!"


def test_fbewma(raw_data, fbewma_data):
    """Test the FBEWMA function."""
    # Setup
    span = 3

    # Testing
    fbewma_df = filters.fbewma(raw_data, span)

    # pytest.approx accounts for floating point errors and such
    assert fbewma_df.to_numpy() == pytest.approx(
        fbewma_data.to_numpy()
    ), "FBEWMA failed!"

    assert raw_data.to_numpy() != pytest.approx(
        fbewma_data.to_numpy()
    ), "Original values modified!"


def test_remove_outliers(raw_data, fbewma_data, mocker, span=2, delta=2):
    """Test the remove outliers function."""
    # Setting up a bug free mock version of fbewma to use in remove_outliers
    fbewma_mock = mocker.patch(
        "hydrobot.filters.fbewma",
        side_effect=fbewma_data,
    )

    # This call of remove outliers should call fbewma_mock in the place of fbewma
    no_outliers = filters.remove_outliers(raw_data, span, delta)
    assert math.isnan(no_outliers["2021-01-01 00:10"]), "Outlier not removed!"
    assert not math.isnan(raw_data["2021-01-01 00:10"]), "Original modified!"


def test_remove_spike(raw_data, fbewma_data, mocker):
    """Test the spike removal function."""
    # Setup
    span = 2
    low_clip = 2
    high_clip = 4
    delta = 2

    # def clip_no_bugs(*args, **kwargs):
    #     return insert_raw_data_gaps(["2021-01-01 00:00", "2021-01-01 00:20"])

    def remove_outliers_no_bugs(*args, **kwargs):
        return insert_fbewma_data_gaps(
            ["2021-01-01 00:00", "2021-01-01 00:10", "2021-01-01 00:20"]
        )

    # I can use the same mocker here because clip wouldn't do anything to this data
    # clip_mock = mocker.patch(
    #     "hydrobot.filters.clip",
    #     side_effect=clip_no_bugs,
    # )

    # outlier_mock = mocker.patch(
    #     "hydrobot.filters.remove_outliers",
    #     side_effect=remove_outliers_no_bugs,
    # )

    spike_removed = filters.remove_spikes(raw_data, span, high_clip, low_clip, delta)
    assert math.isnan(spike_removed["2021-01-01 00:10"]), "Spike not removed!"
    assert not math.isnan(raw_data["2021-01-01 00:10"]), "Original modified!"


def test_remove_range(raw_data):
    """Test the remove range function."""
    a = filters.remove_range(raw_data, "2021-01-01 00:05", "2021-01-01 00:10")
    assert len(a) == 3, "Incorrect number of values removed"
    assert a["2021-01-01 00:00"] == 1.0, "first value compromised"
    assert a["2021-01-01 00:15"] == 4.0, "after value compromised"
    assert a["2021-01-01 00:20"] == 5.0, "end value compromised"

    b = filters.remove_range(raw_data, "2021-01-01 00:03", "2021-01-01 00:14")
    assert b.equals(a), "time rounding error"

    c = filters.remove_range(raw_data, "2021-01-01 00:03", None)
    assert "2021-01-01 00:00" in c.index, "removed first value"
    assert len(c) == 1, "Start None value causes error"

    d = filters.remove_range(raw_data, None, "2021-01-01 00:19")
    assert "2021-01-01 00:20" in d.index, "removed last value"
    assert len(d) == 1, "End None value causes error"

    e = filters.remove_range(raw_data, None, None)
    assert e.empty, "double None causes error"
    assert not raw_data.empty, "Original modified"

    f = filters.remove_range(
        raw_data, "2021-01-01 00:03", "2021-01-01 00:14", insert_gaps="all"
    )
    assert pd.isna(
        f.loc["2021-01-01 00:05"]
    ), "gap failed to be inserted for 'all' case"
    assert pd.isna(
        f.loc["2021-01-01 00:10"]
    ), "gap failed to be inserted for 'all' case"

    g = filters.remove_range(
        raw_data, "2021-01-01 00:03", "2021-01-01 00:14", insert_gaps="start"
    )
    assert pd.isna(
        g.loc["2021-01-01 00:05"]
    ), "gap failed to be inserted for 'start' case"
    assert "2021-01-01 00:10" not in g.index, "incorrect gap inserted for 'start' case"

    h = filters.remove_range(
        raw_data, "2021-01-01 00:03", "2021-01-01 00:14", insert_gaps="end"
    )
    assert "2021-01-01 00:05" not in h.index, "gap failed to be inserted for 'end' case"
    assert pd.isna(h.loc["2021-01-01 00:10"]), "incorrect gap inserted for 'end' case"

    i = filters.remove_range(
        raw_data, "2021-01-01 00:03", "2021-01-01 00:14", insert_gaps="none"
    )
    assert i.isna().sum() == 0, "incorrect gap inserted for 'none' case"

    j = filters.remove_range(
        raw_data,
        "2021-01-01 00:03",
        "2021-01-01 00:14",
        min_gap_length=3,
        insert_gaps="all",
    )
    assert (
        j.isna().sum() == 0
    ), "incorrect gap inserted for 'all' case where gap smaller than min gap."

    k = filters.remove_range(
        raw_data,
        "2021-01-01 00:03",
        "2021-01-01 00:14",
        min_gap_length=3,
        insert_gaps="start",
    )
    assert (
        k.isna().sum() == 0
    ), "incorrect gap inserted for 'start' case where gap smaller than min gap."

    ll = filters.remove_range(
        raw_data,
        "2021-01-01 00:03",
        "2021-01-01 00:14",
        min_gap_length=3,
        insert_gaps="end",
    )
    assert (
        ll.isna().sum() == 0
    ), "incorrect gap inserted for 'end' case where gap smaller than min gap."

    m = filters.remove_range(
        raw_data,
        "2021-01-01 00:03",
        "2021-01-01 00:14",
        min_gap_length=3,
        insert_gaps="none",
    )
    assert (
        m.isna().sum() == 0
    ), "incorrect gap inserted for 'none' case where gap smaller than min gap."


def test_trim_series(raw_data):
    """Testing a trimmed series."""
    raw_check = pd.Series(
        {
            "2021-01-01 00:05": 3,
            "2021-01-01 00:15": 2,
        }
    )
    trimmed = filters.trim_series(raw_data, raw_check)
    assert len(trimmed) == 4, "Trimming returned wrong number"
    assert trimmed["2021-01-01 00:15"] == 4.0, "end value changed"
    assert raw_data["2021-01-01 00:20"] == 5.0, "Original modified"

    untrimmed = filters.trim_series(raw_data, pd.Series({}))
    assert raw_data.equals(untrimmed), "empty check series modified the data"

    raw_check = pd.Series(
        {
            "2021-01-01 00:05": 3,
            "2021-01-01 00:25": 2,
        }
    )
    over_trimmed = filters.trim_series(raw_data, raw_check)
    assert raw_data.equals(
        over_trimmed
    ), "check data beyond standard series modifies data"

    raw_check = pd.Series(
        {
            "2021-01-01 00:07": 3,
        }
    )
    big_trim = filters.trim_series(raw_data, raw_check)
    assert len(big_trim) == 2, "off-centre check data screws things up somehow"


def test_flatline_value_remover(raw_data, constant_data):
    """Testing removal of flatlining values."""
    assert raw_data.equals(
        filters.flatline_value_remover(raw_data)
    ), "Changing data it shouldn't"
    assert raw_data.equals(
        filters.flatline_value_remover(raw_data, 100)
    ), "Changing data it shouldn't when span is too big"

    removed_3 = filters.flatline_value_remover(constant_data, 3)
    assert len(raw_data) == 5, "Original modified"
    assert len(removed_3) == len(constant_data), "shortened data for removed_3"
    assert math.isclose(
        removed_3["2021-01-01 00:35"], 6.1
    ), "Incorrectly removed first consec value"
    assert math.isnan(
        removed_3["2021-01-01 00:40"]
    ), "Failed to remove second consec value"
    assert math.isnan(
        removed_3["2021-01-01 00:45"]
    ), "Failed to remove third consec value"
    assert math.isnan(
        removed_3["2021-01-01 00:50"]
    ), "Failed to remove fourth consec value"
    assert math.isnan(
        removed_3["2021-01-01 00:55"]
    ), "Failed to remove fifth consec value"
    assert math.isclose(
        removed_3["2021-01-01 01:00"], 6.2
    ), "Incorrectly removed first nonconsec value"
    assert math.isclose(
        removed_3["2021-01-01 00:10"], 3.0
    ), "Incorrectly removed value from too short sequence"

    removed_2 = filters.flatline_value_remover(constant_data, 2)
    assert len(removed_2) == len(constant_data), "shortened data for removed_2"
    assert math.isclose(
        removed_2["2021-01-01 00:05"], 3.0
    ), "Incorrectly removed value from start of short sequence"
    assert math.isnan(
        removed_2["2021-01-01 00:10"]
    ), "Failed to consec value from short sequence"
    assert math.isnan(
        removed_2["2021-01-01 00:15"]
    ), "Failed to consec value from short sequence"
    assert math.isclose(
        removed_2["2021-01-01 00:20"], 3.00001
    ), "Incorrectly removed value from end of short sequence"
    assert math.isclose(
        removed_2["2021-01-01 00:35"], 6.1
    ), "Incorrectly removed first consec value2"
    assert math.isnan(
        removed_2["2021-01-01 00:40"]
    ), "Failed to remove second consec value"
    assert math.isnan(
        removed_2["2021-01-01 00:45"]
    ), "Failed to remove third consec value2"
    assert math.isnan(
        removed_2["2021-01-01 00:50"]
    ), "Failed to remove fourth consec value2"
    assert math.isnan(
        removed_2["2021-01-01 00:55"]
    ), "Failed to remove fifth consec value2"
    assert math.isclose(
        removed_2["2021-01-01 01:00"], 6.2
    ), "Incorrectly removed first nonconsec value2"
