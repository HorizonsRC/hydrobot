"""General utilities."""

import re
import urllib.parse
import warnings

import numpy as np
import pandas as pd
import ruamel.yaml
from hilltoppy.utils import get_hilltop_xml
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
    """
    Find the blocks of changes between two series.

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
            # If one series has a timestamp that the other doesn't, treat it as a change.
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


def series_rounder(series: pd.Series | pd.DataFrame, round_frequency: str = "6min"):
    """
    Rounds pandas data to be on the 6-minute mark (or other interval).

    Parameters
    ----------
    series : pd.Series | pd.DataFrame
        The data to have index rounded. Gives warning if index is not a DatetimeIndex
    round_frequency : str
        Frequency alias, default is 6 minutes. See:
        https://pandas.pydata.org/pandas-docs/stable/user_guide/timeseries.html#timeseries-offset-aliases

    Returns
    -------
    pd.Series | pd.DataFrame
        The data with index rounded
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


def find_nearest_indices(base_series, check_series):
    """
    Find the nearest timestamp from another series or dataframe.

    Given two series/dataframes, this function finds the indices of
    the first data that is closest to the indices in the second data.

    e.g. index of 1,2,3,4,5 and 1.2, 3.7 would give 1,4

    Parameters
    ----------
    base_series : pd.Series | pd.DataFrame
        The series to have values drawn from
    check_series : pd.Series | pd.DataFrame
        The series of values to have rounded to the base series

    Returns
    -------
    list[indices]
        A list of indices of the periodic series that are closest to the check series

    """
    nearest_indices = []
    for check_index in check_series.index:
        # Calculate the difference between the check_index and every periodic index
        time_diff = np.abs(base_series.index - check_index)

        # Find the index in standard_series with the minimum time difference
        nearest_index = np.argmin(time_diff)

        nearest_indices.append(nearest_index)

    return nearest_indices


def find_last_indices(base_series, check_series):
    """
    Find the nearest timestamp from another series or dataframe rounding down.

    Given two series/dataframes, this function finds the indices of
    the first series that is closest to the indices in the second series.

    e.g. index of 1,2,3,4,5 and 1.2, 3.7 would give 1,3

    Parameters
    ----------
    base_series : pd.Series | pd.DataFrame
        The series to have values drawn from
    check_series : pd.Series | pd.DataFrame
        The series of values to have rounded

    Returns
    -------
    list[indices]
        A list of indices of the periodic series that are closest to the check series

    """
    nearest_indices = []
    for check_index in check_series.index:
        # Calculate the difference between the check_index and every periodic index
        time_diff = check_index - base_series.index[base_series.index <= check_index]

        # Find the index in standard_series with the minimum time difference
        if not time_diff.empty:
            nearest_index = np.argmin(time_diff)
        else:
            nearest_index = base_series.index[0]

        nearest_indices.append(nearest_index)

    return nearest_indices


def enforce_config_values_not_missing(config_file, parameters_to_check):
    """
    Raises parameters to None if not present in config file.

    Parameters
    ----------
    config_file : str
        Path to config.yaml to modify
    parameters_to_check : [str]
        List of parameters to enforce being part of

    Returns
    -------
    None

    Raises
    ------
    ______
    ValueError
        If any of the parameters are missing
    """
    missing_parameters = []
    yaml = ruamel.yaml.YAML()
    with open(config_file) as fp:
        data = yaml.load(fp)
        for parameter in parameters_to_check:
            if parameter not in data:
                missing_parameters.append(parameter)
    if missing_parameters:
        raise ValueError(
            f"Required parameters missing in config file {config_file}. Add these values to config.yaml "
            f"file:{missing_parameters} (these values can likely be set to None)"
        )


def combine_comments(comment_frame: pd.DataFrame) -> pd.Series:
    """
    For multiple comments in multiple columns, combine comments with column headers as delimiters.

    Parameters
    ----------
    comment_frame : pd.DataFrame
        Comments to be combined

    Returns
    -------
    pd.Series
        All columns combined
    """
    comment_frame = comment_frame.copy()
    output_series = pd.Series(index=comment_frame.index, data="")
    for count, label in enumerate(comment_frame.columns):
        next_part = comment_frame[label]
        next_part[next_part.notna()] = label + ": " + next_part[next_part.notna()]

        if count < len(comment_frame.columns) - 1:
            next_part[next_part.notna()] += "; "
        next_part = next_part.fillna("")

        output_series += next_part
    return output_series


def find_last_time(
    base_url,
    hts,
    site,
    measurement,
):
    """
    Find the last data point in the hts file for a given site/measurement pair.

    Parameters
    ----------
    base_url : str
    hts : str
    site : str
    measurement : str

    Returns
    -------
    pd.Timestamp
    """
    timerange_url = (
        f"{base_url}{urllib.parse.quote(hts)}?Service=Hilltop&Request=TimeRange&Site="
        f"{urllib.parse.quote(site)}&Measurement={urllib.parse.quote(measurement)}"
    )
    hilltop_xml = get_hilltop_xml(timerange_url)
    if hilltop_xml.find("To") is None:
        raise ValueError(
            f"No data found for this site. If no previous processing is done, a from_date is required. "
            f"URL:{timerange_url}"
        )
    return pd.Timestamp(hilltop_xml.find("To").text.split("+")[0], tz=None)


def safe_concat(input_frames):
    """Version of pd.concat that doesn't raise errors for empty dataframes/series."""
    non_empty_input = [i for i in input_frames if not i.empty]
    if non_empty_input:
        return pd.concat(non_empty_input)
    else:
        return pd.DataFrame(columns=input_frames[0].columns)


def measurement_datasource_splitter(measurement_name):
    """Splits Hilltop measurement [datasource] into measurement and datasource."""
    matches = re.search(r"([^\[\n]+)(\[(.+)\])?", measurement_name)
    item_name = matches.groups()[0].strip(" ")
    data_source_name = matches.groups()[2]
    if data_source_name is None:
        data_source_name = item_name
    return item_name, data_source_name
