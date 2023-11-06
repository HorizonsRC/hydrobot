"""Tools for checking how many problems there are with the data."""
import pandas as pd
import numpy as np
from annalist.annalist import Annalist

annalizer = Annalist()


@annalizer.annalize
def gap_finder(data):
    """
    Find gaps in a series of data (indicated by np.isnan()).

    Returns a list of tuples indicating the start of the gap, and the number
    of entries that are NaN

    Parameters:
    -----------
    data : pandas.Series
        Input data to be clipped.

    Returns:
    --------
    List of Tuples
        Each element in the list gives the index value for the start of the gap
        and the length of the gap
    """
    idx0 = np.flatnonzero(np.r_[True, np.diff(np.isnan(data)) != 0, True])
    count = np.diff(idx0)
    idx = idx0[:-1]
    valid_mask = np.isnan(data.iloc[idx])
    out_idx = idx[valid_mask]
    out_count = count[valid_mask]
    out = zip(data.index[out_idx], out_count)

    return list(out)


@annalizer.annalize
def small_gap_closer(series, gap_length):
    """
    Remove small gaps from a series.

    Gaps are defined by a sequential number of np.NaN values
    Small gaps are defined as gaps of length gap_length or less

    Will return series with the nan values in the short gaps removed, and the
    long gaps untouched

    :param series: pandas.Series
        Data which has gaps to be closed
    :param gap_length: integer
        Maximum length of gaps removed, will remove all np.NaN's in consecutive
        runs of gap_length or less
    :return:
    pandas.Series
        Data with any short gaps removed
    """
    gaps = gap_finder(series)
    for gap in gaps:
        # Ask ChatGPT what this means
        if gap[1] <= gap_length:
            mask = ~series.index.isin(
                series.index[
                    series.index.get_loc(gap[0]) : series.index.get_loc(gap[0]) + gap[1]
                ]
            )
            series = series[mask]

    return series


@annalizer.annalize
def check_data_quality_code(series, check_series, measurement, gap_limit=10800):
    """Quality Code Check Data.

    Quality codes data based on the difference between the standard series and
    the check data

    :param series: pd.Series
        Data to be quality coded
    :param check_series: pd.Series
        Check data
    :param measurement: data_sources.Measurement
        Handler for QC comparisons
    :param gap_limit: int (seconds)
        If the nearest real data point is more than this many seconds away, return 200

    :return: List of integers (QC values)
    """
    qc_series = pd.Series({})
    for check_time, check_value in check_series.items():
        adjusted_time = find_nearest_valid_time(series, check_time)
        if abs((adjusted_time - check_time).total_seconds()) < gap_limit:
            qc_value = measurement.find_qc(series[adjusted_time], check_value)
        else:
            qc_value = 200
        qc_series[check_time] = qc_value

    return qc_series


@annalizer.annalize
def find_nearest_time(series, dt):
    """
    Find the time in the series that is closest to dt
    For example for... data series
        pd.Timestamp("2021-01-01 02:00"): 0.0,
        pd.Timestamp("2021-01-01 02:15"): 0.0,
    with dt
        pd.Timestamp("2021-01-01 02:13"): 0.0,
    the result should be the closer pd.Timestamp("2021-01-01 02:15") value

    :param series: pd.Series
        The series indexed by time
    :param dt: Datetime
        Time that may or may nor exactly line up with the series

    :return: Datetime
        The value of dt rounded to the nearest timestamp of the series
    """
    # Make sure it is in the range
    first_timestamp = series.index[0]
    last_timestamp = series.index[-1]
    if dt < first_timestamp or dt > last_timestamp:
        raise Exception

    output_index = series.index.get_indexer([dt], method="nearest")
    return series.index[output_index][0]


@annalizer.annalize
def find_nearest_valid_time(series, dt):
    """
    Find the time in the series that is closest to dt, but ignoring NaN values (gaps)

    :param series: pd.Series
        The series indexed by time
    :param dt: Datetime
        Time that may or may nor exactly line up with the series

    :return: Datetime
        The value of dt rounded to the nearest timestamp of the series
    """
    # Make sure it is in the range
    first_timestamp = series.index[0]
    last_timestamp = series.index[-1]
    if dt < first_timestamp or dt > last_timestamp:
        raise Exception

    series = series.dropna()
    output_index = series.index.get_indexer([dt], method="nearest")
    return series.index[output_index][0]


def base_data_qc_filter(base_series, qc_filter):
    """
    Returns only the base series data for which the next date in the qc_filter is 'true'

    :param base_series: pandas.Series
        Data to be filtered
    :param qc_filter: pandas.Series of booleans
        Dates for which some condition is met or not
    :return: pandas.Series
        Filtered data
    """

    base_filter = qc_filter.reindex(base_series.index, method="bfill").fillna(False)
    return base_series[base_filter]


def base_data_meets_qc(base_series, qc_series, target_qc):
    """
    Returns only the base series data for which the next date in the qc_filter is equal to target_qc
    :param base_series: pandas.Series
        Data to be filtered
    :param qc_series: pandas.Series
        quality code data series, some of which are presumably target_qc
    :param target_qc: int
        target quality code
    :return: pandas.Series
        Filtered data
    """
    return base_data_qc_filter(base_series, qc_series == target_qc)


def diagnose_data(raw_data, base_series, series_list, qc_list):
    """
    Returns description of how much missing data, how much for each QC, etc

    :param raw_data: pandas.Series
        unprocessed data
    :param base_series: pandas.Series
        un-QCed but processed data (spikes removed, small gaps closed)
    :param series_list: list of pandas.Series
        Data for each QC
    :param qc_list: list of ints (QC codes)
        QC codes for each element in series_list
    :return: String
    """

    output_string = ""
    # total time
    first_timestamp = base_series.index[0]
    last_timestamp = base_series.index[-1]
    total_time = last_timestamp - first_timestamp
    output_string += f"Total time examined is {total_time} from {first_timestamp} to {last_timestamp}\n"

    # periods
    ave_period = total_time / len(raw_data)
    output_string += f"Average period between recorded datums is {ave_period}\n"
    gap_time = ave_period * (len(base_series) - len(base_series.dropna()) + 1)
    output_string += (
        f"Missing {gap_time} amount of data, that's {gap_time/total_time*100}%\n"
    )

    # QCs
    for line in list(zip(series_list, qc_list)):
        qc = line[1]
        series = line[0]
        output_string += (
            f"Data that is QC{qc} makes up {len(series.dropna()) / len(base_series) * 100}% of the "
            f"workable data and {len(series.dropna()) / len(raw_data) * 100}% of the time period\n"
        )
    output_string += f"Now it's your job to figure out if that's good enough"
    return output_string
