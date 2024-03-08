"""General utilities."""

import numpy as np
import pandas as pd

MOWSECS_OFFSET = 946771200


def mowsecs_to_timestamp(mowsecs):
    """
    Convert MOWSECS (Ministry of Works Seconds) index to datetime index.

    Parameters
    ----------
    index : pd.Index
        The input index in MOWSECS format.

    Returns
    -------
    pd.DatetimeIndex
        The converted datetime index.

    Notes
    -----
    This function takes an index representing time in Ministry of Works Seconds
    (MOWSECS) format and converts it to a pandas DatetimeIndex.

    Examples
    --------
    >>> mowsecs_index = pd.Index([0, 1440, 2880], name="Time")
    >>> converted_index = mowsecs_to_datetime_index(mowsecs_index)
    >>> isinstance(converted_index, pd.DatetimeIndex)
    True
    """
    try:
        mowsec_time = int(mowsecs)
    except ValueError as e:
        raise TypeError("Expected something that is parseable as an integer") from e

    unix_time = mowsec_time - MOWSECS_OFFSET
    timestamp = pd.Timestamp(unix_time, unit="s")
    return timestamp


def timestamp_to_mowsecs(timestamp):
    """
    Convert MOWSECS (Ministry of Works Seconds) index to datetime index.

    Parameters
    ----------
    index : pd.Index
        The input index in MOWSECS format.

    Returns
    -------
    pd.DatetimeIndex
        The converted datetime index.

    Notes
    -----
    This function takes an index representing time in Ministry of Works Seconds
    (MOWSECS) format and converts it to a pandas DatetimeIndex.

    Examples
    --------
    >>> mowsecs_index = pd.Index([0, 1440, 2880], name="Time")
    >>> converted_index = mowsecs_to_datetime_index(mowsecs_index)
    >>> isinstance(converted_index, pd.DatetimeIndex)
    True
    """
    try:
        timestamp = pd.Timestamp(timestamp)
    except ValueError as e:
        raise TypeError("Expected something that is parseable as an integer") from e

    return int((timestamp.timestamp()) + MOWSECS_OFFSET)


def mowsecs_to_datetime_index(index):
    """
    Convert MOWSECS (Ministry of Works Seconds) index to datetime index.

    Parameters
    ----------
    index : pd.Index
        The input index in MOWSECS format.

    Returns
    -------
    pd.DatetimeIndex
        The converted datetime index.

    Notes
    -----
    This function takes an index representing time in Ministry of Works Seconds
    (MOWSECS) format and converts it to a pandas DatetimeIndex.

    Examples
    --------
    >>> mowsecs_index = pd.Index([0, 1440, 2880], name="Time")
    >>> converted_index = mowsecs_to_datetime_index(mowsecs_index)
    >>> isinstance(converted_index, pd.DatetimeIndex)
    True
    """
    try:
        mowsec_time = index.astype(np.int64)
    except ValueError as e:
        raise TypeError("These don't look like mowsecs. Expecting an integer.") from e
    unix_time = mowsec_time.map(lambda x: x - MOWSECS_OFFSET)
    timestamps = unix_time.map(
        lambda x: pd.Timestamp(x, unit="s") if x is not None else None
    )
    datetime_index = pd.to_datetime(timestamps)
    return datetime_index


def datetime_index_to_mowsecs(index):
    """
    Convert datetime index to MOWSECS (Ministry of Works Seconds).

    Parameters
    ----------
    index : pd.DatetimeIndex
        The input datetime index.

    Returns
    -------
    pd.Index
        The converted MOWSECS index.

    Notes
    -----
    This function takes a pandas DatetimeIndex and converts it to an index
    representing time in Ministry of Works Seconds (MOWSECS) format.

    Examples
    --------
    >>> datetime_index = pd.date_range("2023-01-01", periods=3, freq="D")
    >>> mowsecs_index = datetime_index_to_mowsecs(datetime_index)
    >>> isinstance(mowsecs_index, pd.Index)
    True
    """
    return (index.astype(np.int64) // 10**9) + MOWSECS_OFFSET


def merge_series(series_a, series_b, tolerance=1e-09):
    """
    Combine two series which contain partial elements of the same dataset.

    For series 1:a, 2:b and series 1:a, 3:c, will give 1:a, 2:b, 3:c

    Will give an error if series contains contradicting data

    If difference in data is smaller than tolerance, the values of the first series are used

    Parameters
    ----------
    series_a : pd.Series
        One series to combine (preferred when differences are below tolerance)
    series_b : pd.Series
        Second series to combine (overwritten when differences are below tolerance)
    tolerance : numeric
        Maximum allowed difference between the two series for the same timestamp

    Returns
    -------
    pd.Series
        Combined series
    """
    combined = series_a.combine_first(series_b)
    diff = abs(series_b.combine_first(series_a) - combined)
    if max(diff) > tolerance:
        raise ValueError
    else:
        return combined
