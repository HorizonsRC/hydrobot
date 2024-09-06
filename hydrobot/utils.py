"""General utilities."""

import warnings

import numpy as np
import pandas as pd
from pandas.tseries.frequencies import to_offset

MOWSECS_OFFSET = 946771200


def mowsecs_to_timestamp(mowsecs):
    """
    Convert MOWSECS (Ministry of Works Seconds) to timestamp.

    Parameters
    ----------
    mowsecs : str | int
        Number of seconds since MOWSECS epoch.

    Returns
    -------
    pd.Timestamp
        The converted datetime.

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
    Convert timestamp to MOWSECS (Ministry of Works Seconds).

    Parameters
    ----------
    timestamp : pd.Timestamp | np.datetime64
        The input timestamp.

    Returns
    -------
    int
        Number of seconds since MOWSECS epoch.

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


def change_blocks(raw_series, changed_series):
    """Find the blocks of changes between two series.

    Parameters
    ----------
    raw_series : pd.Series
        The original series
    changed_series : pd.Series
        The series with changes

    Returns
    -------
    list
        A list of tuples where each tuple represents a block of change.
        The first element of the tuple is the start of the block and the second
        element is the end of the block.

    Notes
    -----
    The function takes two series and finds the blocks of changes between them.
    The function returns the blocks of changes as a list of tuples where each
    tuple represents a block of change. The first element of the tuple is the
    start of the block and the second element is the end of the block.
    """
    changed_block_list = []
    start_index = None

    raw_iter = iter(raw_series.items())
    changed_iter = iter(changed_series.items())
    raw_next = next(raw_iter, None)
    changed_next = next(changed_iter, None)

    while raw_next is not None or changed_next is not None:
        raw_date, raw_val = raw_next if raw_next else (None, None)
        changed_date, changed_val = changed_next if changed_next else (None, None)

        if raw_date != changed_date:
            # If one series has a timestamp that the other doesn't, treat it as a change
            # Change block goes from the raw timestamp that is missing in the edit to the
            # next value in the edit, i.e. the entire gap.
            if start_index is None:
                start_index = raw_date
        elif raw_val != changed_val:
            # If the values at the same timestamp are different, treat it as a change
            if start_index is None:
                # Start of a changed block
                start_index = raw_date
        else:
            if start_index is not None:
                # End of a changed block
                changed_block_list.append((start_index, raw_date))
                start_index = None

        # Move to the next timestamp in each series
        if raw_date == changed_date:
            raw_next = next(raw_iter, None)
            changed_next = next(changed_iter, None)
        elif (raw_date is None) or raw_date < changed_date:
            raw_next = next(raw_iter, None)
        else:
            changed_next = next(changed_iter, None)

    if start_index is not None:
        changed_block_list.append((start_index, raw_series.index[-1]))

    return changed_block_list


def merge_all_comments(hill_checks, pwq_checks, s123_checks, ncrs):
    """Make a sorted dataframe of all comments from all sources.

    Parameters
    ----------
    hill_checks : pd.DataFrame
        Hilltop check data
    pwq_checks : pd.DataFrame
        Provisional water quality data
    s123_checks : pd.DataFrame
        Survey123 inspection data
    ncrs : pd.DataFrame
        Non-conformance reports

    Returns
    -------
    pd.DataFrame
        A sorted dataframe of all comments from all sources

    Notes
    -----
    The function takes four dataframes of comments from different sources and
    combines them into a single dataframe. The function returns a sorted dataframe
    of all comments from all sources.
    """
    hill_checks = hill_checks.rename(columns={"Water Temperature Check": "Temp Check"})
    hill_checks = hill_checks.reset_index()
    pwq_checks = pwq_checks.reset_index()
    s123_checks = s123_checks.reset_index()
    ncrs = ncrs.reset_index()

    hill_checks["Source"] = "Hilltop Check Data"
    pwq_checks["Source"] = "Provisional Water Quality"
    s123_checks["Source"] = "Survey123 Inspections"
    ncrs["Source"] = "Non-conformance Reports"

    all_comments_list = [
        hill_checks[["Time", "Comment", "Source"]],
        pwq_checks[["Time", "Comment", "Source"]],
        s123_checks[["Time", "Comment", "Source"]],
        ncrs[["Time", "Comment", "Source"]],
    ]
    all_comments_list = [i for i in all_comments_list if not i.empty]

    all_comments = pd.concat(
        all_comments_list,
        ignore_index=True,
        sort=False,
    )
    all_comments = all_comments.dropna(axis=1, how="all")

    if not all_comments.empty:
        all_comments["Time"] = all_comments["Time"].dt.strftime("%Y-%m-%d %H:%M:%S")

        all_comments = all_comments.sort_values(by="Time")

    return all_comments


def compare_two_qc_take_min(qc_series_1, qc_series_2):
    """
    Takes two QC series and takes the lowest QC in the list for each time period.

    Parameters
    ----------
    qc_series_1 : pd.Series
        One series
    qc_series_2 : pd.Series
        Other series

    Returns
    -------
    pd.Series
        Combined series
    """
    combined_index = qc_series_1.index.union(qc_series_2.index)
    with pd.option_context("future.no_silent_downcasting", True):
        full_index_1 = (
            qc_series_1.reindex(combined_index, method="ffill")
            .replace(np.nan, np.Inf)
            .infer_objects(copy=False)
        )
        full_index_2 = (
            qc_series_2.reindex(combined_index, method="ffill")
            .replace(np.nan, np.Inf)
            .infer_objects(copy=False)
        )

    minimised_qc_series_with_dup = np.minimum(full_index_1, full_index_2)
    minimised_qc_series = minimised_qc_series_with_dup.loc[
        minimised_qc_series_with_dup.shift() != minimised_qc_series_with_dup
    ]
    return minimised_qc_series.astype(np.int64)


def compare_qc_list_take_min(list_of_qc_series):
    """
    Takes a list of QC series and takes the lowest QC in the list for each time period.

    Parameters
    ----------
    list_of_qc_series : [pd.Series]
        Each element of this list is a QC_series to combine (via min)

    Returns
    -------
    pd.Series
        The combined series
    """
    if len(list_of_qc_series) == 0:
        raise ValueError("Can't be empty mate")
    else:
        qc_series = list_of_qc_series[0]
        for q in list_of_qc_series[1:]:
            qc_series = compare_two_qc_take_min(qc_series, q)
        return qc_series


def correct_dissolved_oxygen(diss_ox, atm_pres, ap_altitude, do_altitude):
    """
    Corrects the dissolved oxygen.

    Only corrects for atmospheric pressure - that seems to be how we've done this for a while

    Parameters
    ----------
    diss_ox : pd.Series
        Dissolved oxygen uncorrected
    atm_pres : pd.Series
        Atmospheric pressure from nearby site
    ap_altitude : numeric
        Altitude of atmospheric pressure sensor (relative to sea level or w/e)
    do_altitude : numeric
        Altitude of dissolved oxygen sensor (relative to sea level or w/e, but make sure it's the same standard as
        altitude)

    Returns
    -------
    pd.Series
        Dissolved oxygen series, but corrected
    """
    atm_pres += (ap_altitude - do_altitude) * 0.1222

    # sea level atm pressure is 1013.25
    corr_diss_ox = diss_ox * 1013.25 / atm_pres
    return corr_diss_ox


def series_rounder(series: pd.Series, round_frequency: str = "6min"):
    """
    Rounds series to be on the 6-minute mark (or other interval).

    Parameters
    ----------
    series : pd.Series
        The series to have index rounded. Gives warning if index is not a DatetimeIndex
    round_frequency : str
        Frequency alias, default is 6 minutes. See:
        https://pandas.pydata.org/pandas-docs/stable/user_guide/timeseries.html#timeseries-offset-aliases

    Returns
    -------
    pd.Series
        The series with index rounded
    """
    rounded_series = series.copy()
    # noinspection PyUnresolvedReferences
    if not isinstance(rounded_series.index, pd.core.indexes.datetimes.DatetimeIndex):
        warnings.warn(
            "INPUT_WARNING: Index is not DatetimeIndex, index type will be changed",
            stacklevel=2,
        )
    series_index = pd.DatetimeIndex(rounded_series.index) + pd.Timedelta(nanoseconds=1)
    rounded_series.index = series_index.round(round_frequency)
    return rounded_series


def rainfall_six_minute_repacker(series: pd.Series):
    """
    Repacks SCADA rainfall (rainfall bucket events) as 6 minute totals.

    Parameters
    ----------
    series : pd.Series
        SCADA rainfall series to be repacked as a 6 minute totals series
        expects a datetime index, will throw warning if it is not while it converts

    Returns
    -------
    pd.Series
        Repacked series with datetime index
    """
    series = series.copy()

    if not isinstance(series.index, pd.DatetimeIndex):
        warnings.warn(
            "INPUT_WARNING: Index is not DatetimeIndex, index type will be changed",
            stacklevel=2,
        )
        series.index = pd.DatetimeIndex(series.index)

    scada_index = series.index
    floor_index = scada_index.floor("6min")
    ceil_index = scada_index.ceil("6min")

    diff_filter = scada_index.diff() < pd.Timedelta(minutes=6)
    dup_filter = floor_index.duplicated()

    # Case 1, diff > 6

    time_delta_index_case1 = (scada_index - floor_index) / pd.Timedelta(minutes=6)

    floor_series = series[~diff_filter] * (1 - time_delta_index_case1[~diff_filter])
    floor_series.index = floor_index[~diff_filter]

    ceil_series = series[~diff_filter] * time_delta_index_case1[~diff_filter]
    ceil_series.index = ceil_index[~diff_filter]

    case1 = pd.concat([ceil_series, floor_series]).round()
    case1 = case1.groupby(case1.index).sum()

    # Case 2, diff < 6 & last scada within timespan

    case2 = series[diff_filter & dup_filter]
    case2.index = ceil_index[diff_filter & dup_filter]
    case2 = case2.groupby(case2.index).sum()

    # Case 3, diff < 6 & last scada in other timespan

    time_delta_index_case3 = (scada_index - floor_index) / (scada_index.diff())

    floor_series = series[diff_filter & ~dup_filter] * (
        1 - time_delta_index_case3[diff_filter & ~dup_filter]
    )
    floor_series.index = floor_index[diff_filter & ~dup_filter]

    ceil_series = (
        series[diff_filter & ~dup_filter]
        * time_delta_index_case3[diff_filter & ~dup_filter]
    )
    ceil_series.index = ceil_index[diff_filter & ~dup_filter]

    case3 = pd.concat([ceil_series, floor_series]).round()
    case3 = case3.groupby(case3.index).sum()

    # Putting it together

    rainfall_series = pd.concat([case1, case2, case3])
    rainfall_series = rainfall_series.groupby(rainfall_series.index).sum()

    # fill it up with zeroes
    rainfall_series = rainfall_series.asfreq(freq="6min", fill_value=0.0)

    return rainfall_series


def check_data_ramp_and_quality(std_series: pd.Series, check_series: pd.Series):
    """
    Ramps standard data to fit the check data.

    Parameters
    ----------
    std_series : pd.Series
        The series to be ramped. Values are required at each check value (can be zero)
    check_series : pd.Series
        The data to ramp it to

    Returns
    -------
    (pd.Series, pd.Series)
        First element is std_series but ramped
        Second element is quality_series
    """
    # Avoid side effects
    std_series = std_series.copy()
    check_series = check_series.copy()

    # How much rainfall has occurred according to scada
    incremental_series = std_series.cumsum()

    # Filter to when checks occur
    try:
        recorded_totals = incremental_series[check_series.index]
    except KeyError as e:
        raise KeyError("Check data times not found in the standard series") from e

    # Multiplier of difference between check and scada
    scada_difference = check_series / recorded_totals.diff()
    # Fill out to all scada events
    multiplier = scada_difference.reindex(std_series.index, method="bfill")

    # Multiply to find std_data
    std_series = std_series * multiplier.astype(np.float64).fillna(0.0)

    # Boolean whether it meets qc 600 standard
    points0 = (scada_difference >= 0.9) & (scada_difference <= 1.1)
    points3 = ((scada_difference >= 0.8) & (scada_difference <= 1.2)) & ~(
        (scada_difference >= 0.9) & (scada_difference <= 1.1)
    )
    points12 = ~((scada_difference >= 0.8) & (scada_difference <= 1.2))

    # Either QC 600 or 400
    # noinspection PyUnresolvedReferences
    quality_code = (
        points0.astype(np.float64) * 0
        + points3.astype(np.float64) * 3
        + points12.astype(np.float64) * 12
    )
    # Shift quality codes for hilltop convention
    quality_code = quality_code.shift(periods=-1)
    quality_code = quality_code.fillna(-1000).astype(np.int64)

    return std_series, quality_code


def add_empty_rainfall_to_std(std_series: pd.Series, check_series: pd.Series):
    """
    Add zeroes to the std_series where checks happen (if no SCADA event then).

    Parameters
    ----------
    std_series : pd.Series
        The series which might be missing the zeroes
    check_series : pd.Series
        Where to add the zeroes if they don't exist

    Returns
    -------
    pd.Series
        std_series with zeroes added

    """
    # Prevent side effects
    std_series = std_series.copy()
    check_series = check_series.copy()

    # Find places for new zeroes
    additional_index_values = check_series.index.difference(std_series.index)
    additional_series = pd.Series(0, additional_index_values)

    if not additional_series.empty:
        std_series = pd.concat([std_series, additional_series])
    std_series = std_series.sort_index()

    return std_series


def infer_frequency(index: pd.DatetimeIndex, method="strict"):
    """
    Infer the frequency of a series using pandas infer_freq.

    Parameters
    ----------
    index : pd.DatetimeIndex
        The index to infer the frequency of
    method : str
        The method to use to infer the frequency. Default is 'strict' Options are:
        - strict: Raise an error if the frequency cannot be inferred.
        - mode: Use the mode of the intervals between timestamps as the frequency.
        - raise: Raise an error if the frequency cannot be inferred.

    Returns
    -------
    str
        The inferred frequency of the series
    """
    if not isinstance(index, pd.DatetimeIndex):
        warnings.warn(
            "INPUT_WARNING: Index is not DatetimeIndex, index type will be changed",
            stacklevel=2,
        )
        try:
            index = pd.DatetimeIndex(index)
        except ValueError as e:
            print(index)
            raise ValueError("Could not convert index to DatetimeIndex") from e
    freq = pd.infer_freq(index)

    if freq is None and method == "strict":
        return None
    if freq is None and method == "raise":
        raise ValueError(
            "Could not infer frequency of the series. "
            "Either specify the frequency or remove non-regular timestamps."
        )
    elif freq is None and method == "mode":
        # Calculate the intervals between all DatetimeIndex timestamps in the series
        intervals = index.to_series().diff()

        # Calculate the mode of the intervals
        mode_freq = intervals.mode().iloc[0]

        # return the mode timedelta as a frequency string
        return to_offset(pd.Timedelta(mode_freq)).freqstr
    else:
        return pd.infer_freq(index)
