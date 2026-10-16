"""Tests for resume_point: where should processing pick up from?

BACKGROUND
----------
Hydrobot processes a site's data in chunks, then uploads the result to an
ARCHIVE. Next time, it needs to know how far the last run got, so it can
start from there. resume_point answers that, using two things fetched from
the archive:

    std     The standard (value) series, fetched with quality shown. One row per
            data point, with a "Quality" column holding that point's quality code.
    qual    The quality series. One entry each time the quality code CHANGES
            (not one per data point).

See QUALITY_CODES.rst for more information on NEMS quality code standards.

The rule being tested: resume from the LATER of
    (a) the last std point with a non-zero quality, and
    (b) the last entry in the quality series (picks up QC 100 checkpoints).
resume_point does no fetching, it is a pure function, so these tests just feed
it small hand-made tables.
"""


import numpy as np
import pandas as pd

from hydrobot.orchestration.resume import resume_point


def std(points):
    """Build a standard-series table from (timestamp, quality) pairs.

    ``std([("2025-01-01 00:00", 600), ("2025-01-01 01:00", None)])`` gives two
    rows. ``None`` means "no quality value at all", stored as NaN. (0 also
    means unprocessed; see the zero-quality tests below.) The data values
    themselves don't matter to resume_point, so every row gets 1.0.
    """

    idx = pd.to_datetime([t for t, _ in points])
    q = [np.nan if v is None else v for _, v in points]

    return pd.DataFrame({"Value": 1.0, "Quality": q}, index=idx)


def qual(points):
    """Build a quality series from (timestamp, quality code) pairs.

    ``qual([("2026-10-22T11:00:00", 100)])`` is a series with a single entry:
    a QC 100 point at that time.
    """
    idx = pd.to_datetime([t for t, _ in points])
    return pd.Series([v for _, v in points], index=idx, dtype=float)


# Reusable "nothing there" inputs, for tests where on of the two is empty.
EMPTY_STD = std([])
EMPTY_QUAL = qual([])

def test_checkpoint_after_last_data_wins():
    # Recreated from real archive response: the last data point is at 21 Oct
    # 18:00 (QC 600), then a QC 100 "missing record" checkpoint at 22 Oct 11:00.
    # The checkpoint says processing got to 11:00, so resume from there, even
    # though there's no data between 18:00 and 11:00
    s = std([("2025-10-21T18:00:00", 600)])
    q = qual([("2025-10-22T11:00:00", 100)])
    assert resume_point(s, q) == pd.Timestamp("2025-10-22T11:00:00")


def test_trailing_chunk_without_quality_is_ignored():
    # Four points: the last two have no quality, meaning that they were copied up
    # to the archive without being processed. They don't count as done, so
    # we resume from the last point that DID have quality (01:00), not 03:00.
    s = std([("2025-01-01 00:00", 600), ("2025-01-01 01:00", 600),
             ("2025-01-01 02:00", None), ("2025-01-01 03:00", None)])
    q = qual([("2025-01-01 00:00", 600)])
    assert resume_point(s, q) == pd.Timestamp("2025-01-01 01:00")


def test_unchecked_qc200_counts():
    # Sites with no check data are archived as QC 200. That's still
    # "processed", so it must count (and there's no quality series needed).
    s = std([("2025-01-01 00:00", 200), ("2025-01-01 01:00", 200)])
    assert resume_point(s, EMPTY_QUAL) == pd.Timestamp("2025-01-01 01:00")


def test_data_later_than_checkpoint_wins():
    # The mirror image of the first tests: here the data runs PAST an old
    # checkpoint, so the later data point is the answer, not the checkpoint.
    s = std([("2025-01-02 00:00", 600)])
    q = qual([("2025-01-01 00:00", 100)])
    assert resume_point(s, q) == pd.Timestamp("2025-01-02 00:00")


def test_gap_in_middle_is_irrelevant():
    # A two-month hole in the data between points is fine. We only ever
    # look at the END of the series, so gaps in the middle can't matter.
    s = std([("2025-01-01 00:00", 600), ("2025-03-01 00:00", 600)])
    assert resume_point(s, EMPTY_QUAL) == pd.Timestamp("2025-03-01 00:00")


def test_only_quality_series_present():
    # No standard data at all, just a checkpoint. The checkpoint alone is
    # enough to say where we got to.
    q = qual([("2025-01-01 00:00", 100)])
    assert resume_point(EMPTY_STD, q) == pd.Timestamp("2025-01-01 00:00")


def test_all_points_unprocessed_and_no_quality_series():
    # Data exists, but none of it has quality, and there's no checkpoint:
    # everything was copied up unprocessed, so nothing counts as done.
    # None means "never processed". Whether that's an error is up to the caller.
    s = std([("2025-01-01 00:00", None)])
    assert resume_point(s, EMPTY_QUAL) is None


def test_nothing_at_all_means_never_processed():
    # Brand new series: nothing in the archive in either table.
    assert resume_point(EMPTY_STD, EMPTY_QUAL) is None


def test_zero_quality_means_unprocessed():
    # Quality 0 is the real "unprocessed" code (as opposed to NaN, which is
    # what a missing value looks like). The two trailing 0s are ignored just
    # like the NaN case above, so we resume from the QC 600 point.
    s = std([("2025-01-01 00:00", 600), ("2025-01-01 01:00", 0),
             ("2025-01-01 02:00", 0)])
    assert resume_point(s, EMPTY_QUAL) == pd.Timestamp("2025-01-01 00:00")


def test_only_zero_quality_means_never_processed():
    # Every point is 0 and there's no checkpoint: same as "never processed".
    s = std([("2025-01-01 00:00", 0)])
    assert resume_point(s, EMPTY_QUAL) is None

