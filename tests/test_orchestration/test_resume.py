import numpy as np
import pandas as pd

from hydrobot.orchestration.resume import resume_point


def std(points):
    """points: list of (tiemstamp, quality-or-None)."""
    idx = pd.to_datetime([t for t, _ in points])
    q = [np.nan if v is None else v for _, v in points]

    return pd.DataFrame({"Value": 1.0, "Quality": q}, index=idx)

def qual(points):
    idx = pd.to_datetime([t for t, _ in points])
    return pd.Series([v for _, v in points], index=idx, dtype=float)

EMPTY_STD = std([])
EMPTY_QUAL = qual([])

def test_checkpoint_after_last_data_wins():
    # Recreated from real archive response:
    # last data 21 Oct 18:00 (QC600), then a QC100
    # "missing record" checkpoint at 22 Oct 11:00.
    s = std([("2025-10-21T18:00:00", 600)])
    q = qual([("2025-10-22T11:00:00", 100)])
    assert resume_point(s, q) == pd.Timestamp("2025-10-22T11:00:00")


def test_trailing_chunk_without_quality_is_ignored():
    s = std([("2025-01-01 00:00", 600), ("2025-01-01 01:00", 600),
             ("2025-01-01 02:00", None), ("2025-01-01 03:00", None)])
    q = qual([("2025-01-01 00:00", 600)])
    assert resume_point(s, q) == pd.Timestamp("2025-01-01 01:00")


def test_unchecked_qc200_counts():
    s = std([("2025-01-01 00:00", 200), ("2025-01-01 01:00", 200)])
    assert resume_point(s, EMPTY_QUAL) == pd.Timestamp("2025-01-01 01:00")


def test_data_later_than_checkpoint_wins():
    s = std([("2025-01-02 00:00", 600)])
    q = qual([("2025-01-01 00:00", 100)])
    assert resume_point(s, q) == pd.Timestamp("2025-01-02 00:00")


def test_gap_in_middle_is_irrelevant():
    s = std([("2025-01-01 00:00", 600), ("2025-03-01 00:00", 600)])
    assert resume_point(s, EMPTY_QUAL) == pd.Timestamp("2025-03-01 00:00")


def test_only_quality_series_present():
    q = qual([("2025-01-01 00:00", 100)])
    assert resume_point(EMPTY_STD, q) == pd.Timestamp("2025-01-01 00:00")


def test_all_points_unprocessed_and_no_quality_series():
    s = std([("2025-01-01 00:00", None)])
    assert resume_point(s, EMPTY_QUAL) is None


def test_nothing_at_all_means_never_processed():
    assert resume_point(EMPTY_STD, EMPTY_QUAL) is None


