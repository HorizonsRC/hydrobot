"""Tools for checking how many problems there are with the data"""
import pandas as pd
import numpy as np


def gap_finder(data):
    """
    Finds gaps in a series of data (indicated by np.isnan())

    Returns a list of tuples indicating the start of the gap, and the number of entries that are NaN

    Parameters:
    -----------
    data : pandas.Series
        Input data to be clipped.

    Returns:
    --------
    List of Tuples
        Each element in the list gives the index value for the start of the gap and the length of the gap
    """

    idx0 = np.flatnonzero(np.r_[True, np.diff(np.isnan(data)) != 0, True])
    count = np.diff(idx0)
    idx = idx0[:-1]
    valid_mask = np.isnan(data.iloc[idx])
    out_idx = idx[valid_mask]
    out_count = count[valid_mask]
    out = zip(data.index[out_idx], out_count)

    return list(out)


def small_gap_closer(series, gap_length):
    """
    Removes small gaps from a series

    Gaps are defined by a sequential number of np.NaN values
    Small gaps are defined as gaps of length gap_length or less

    Will return series with the nan values in the short gaps removed, and the long gaps untouched

    :param series: pandas.Series
        Data which has gaps to be closed
    :param gap_length: integer
        Maximum length of gaps removed, will remove all np.NaN's in consecutive runs of gap_length or less
    :return:
    pandas.Series
        Data with any short gaps removed
    """

    gaps = gap_finder(series)
    for gap in gaps:
        if gap[1] <= gap_length:
            mask = ~series.index.isin(
                series.index[
                    series.index.get_loc(gap[0]) : series.index.get_loc(gap[0]) + gap[1]
                ]
            )
            series = series[mask]

    return series


def check_data_quality_code(series, check_series, measurement):
    """
    Quality codes data based on the difference between the standard series and the check data

    :param series: pd.Series
        Data to be quality coded
    :param check_series: pd.Series
        Check data
    :param measurement: data_sources.Measurement
        Handler for QC comparisons

    :return:
    """
    return []
