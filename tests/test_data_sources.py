"""Test the data_sources module."""
import pytest
from annalist.annalist import Annalist

import hydrobot.data_sources as data_sources

ann = Annalist()
ann.configure()


@pytest.mark.dependency(name="test_get_measurement_dict")
def test_get_measurement_dict():
    """Testing the measurement dictionary."""
    m_dict = data_sources.get_qc_evaluator_dict()
    assert isinstance(m_dict, dict), "not a dict somehow"
    assert (
        "Water Temperature [Dissolved Oxygen sensor]" in m_dict
    ), "Missing data source water temp"
    assert (
        m_dict["Water Temperature [Dissolved Oxygen sensor]"].qc_500_limit > 0
    ), "Water temp qc_500 limit not set up correctly"


@pytest.mark.dependency(depends=["test_get_measurement_dict"])
def test_get_measurement():
    """Testing the get_measurement method."""
    wt_meas = data_sources.get_qc_evaluator(
        "Water Temperature [Dissolved Oxygen sensor]"
    )
    assert wt_meas.qc_500_limit > 0, "Water temp qc_500 limit not set up correctly"
    assert wt_meas.find_qc(1.3, 0) == 400, "bad data not given bad qc"
    assert wt_meas.find_qc(1, 0) == 500, "fair data not given fair qc"
    assert wt_meas.find_qc(0.7, 0) == 600, "good data not given good qc"

    stage_meas = data_sources.get_qc_evaluator("Water level statistics: Point Sample")
    assert stage_meas.find_qc(1999, 1988) == 400, "bad data not given bad qc, static"
    assert (
        stage_meas.find_qc(1999, 1990) == 500
    ), "fair data not given fair qc, static low"
    assert (
        stage_meas.find_qc(1999, 1995) == 500
    ), "fair data not given fair qc, static high"
    assert stage_meas.find_qc(1999, 1997) == 600, "good data not given good qc, perc"

    assert stage_meas.find_qc(2001, 1990) == 400, "bad data not given bad qc, perc"
    assert (
        stage_meas.find_qc(2001, 1992) == 500
    ), "fair data not given fair qc, perc low"
    assert (
        stage_meas.find_qc(2001, 1996) == 500
    ), "fair data not given fair qc, perc high"
    assert stage_meas.find_qc(2001, 1998) == 600, "good data not given good qc, perc"

    assert (
        stage_meas.find_qc(10000, 9949) == 400
    ), "bad data not given bad qc, high perc"
    assert (
        stage_meas.find_qc(10000, 9951) == 500
    ), "fair data not given fair qc, high perc low"
    assert (
        stage_meas.find_qc(10000, 9979) == 500
    ), "fair data not given fair qc, high perc high"
    assert (
        stage_meas.find_qc(10000, 9981) == 600
    ), "good data not given good qc, high perc"

    assert stage_meas.find_qc(0, 11) == 400, "bad data not given bad qc, low static"
    assert (
        stage_meas.find_qc(0, 9) == 500
    ), "fair data not given fair qc, low static low"
    assert (
        stage_meas.find_qc(0, 4) == 500
    ), "fair data not given fair qc, low static high"
    assert (
        stage_meas.find_qc(0, 2) == 600
    ), "good data not given good qc, low static perc"

    do_meas = data_sources.get_qc_evaluator("DO Saturation")
    assert do_meas.find_qc(100, 107.9) == 600, "data at 100, should be qc600"
    assert do_meas.find_qc(100, 108.1) == 500, "data at 100, should be qc500 not 600"
    assert do_meas.find_qc(100, 115.9) == 500, "data at 100, should be qc500 not 400"
    assert do_meas.find_qc(100, 116.1) == 400, "data at 100, should be qc400"

    assert do_meas.find_qc(0, 2.9) == 600, "data at 0, should be qc600"
    assert do_meas.find_qc(0, 3.1) == 500, "data at 0, should be qc500 not 600"
    assert do_meas.find_qc(0, 5.9) == 500, "data at 0, should be qc500 not 400"
    assert do_meas.find_qc(0, 6.1) == 400, "data at 0, should be qc400"
