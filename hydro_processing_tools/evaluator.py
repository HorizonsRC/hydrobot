"""Tools for checking how many problems there are with the data"""
import pandas as pd
import numpy as np


def gap_finder(data):
    """
    Finds gaps in a series of data (defined by isnull())

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
    return [o for o in out]
