"""Tools for checking quality and finding problems in the data."""
import warnings

import numpy as np
import pandas as pd
from annalist.annalist import Annalist

from hydrobot.data_sources import QualityCodeEvaluator

annalizer = Annalist()


def gap_finder(data: pd.Series):
    """
    Find gaps in a series of data (indicated by np.isnan()).

    Returns a list of tuples indicating the start of the gap, and the number
    of entries that are NaN

    Parameters
    ----------
    data : pandas.Series
        Input data to be clipped.

    Returns
    -------
    List of Tuples
        Each element in the list gives the index value for the start of the gap
        and the length of the gap
    """
    idx0 = np.flatnonzero(np.r_[True, np.diff(np.isnan(data)) != 0, True])
    count = np.diff(idx0)
    idx = idx0[:-1]
    valid_mask = pd.isna(data.iloc[idx])
    out_idx = idx[valid_mask]
    out_count = count[valid_mask]
    indices = data.iloc[out_idx].index
    out = zip(indices, out_count, strict=True)

    return list(out)


def small_gap_closer(series: pd.Series, gap_limit: int) -> pd.Series:
    """
    Remove small gaps from a series.

    Gaps are defined by a sequential number of np.NaN values
    Small gaps are defined as gaps of length gap_length or less.

    Will return series with the nan values in the short gaps removed, and the
    long gaps untouched.

    Parameters
    ----------
    series : pandas.Series
        Data which has gaps to be closed
    gap_limit : integer
        Maximum length of gaps removed, will remove all np.NaN's in consecutive runs
        of gap_length or less

    Returns
    -------
    pandas.Series
        Data with any short gaps removed
    """
    gaps = gap_finder(series)
    for gap in gaps:
        if gap[1] <= gap_limit:
            # Determine the range of rows to remove
            mask = ~series.index.isin(
                series.index[
                    series.index.get_loc(gap[0]) : series.index.get_loc(gap[0]) + gap[1]
                ]
            )
            # Remove the bad rows
            series = pd.Series(series[mask])
    return series


def check_data_quality_code(
    series: pd.Series,
    check_series: pd.Series,
    qc_evaluator: QualityCodeEvaluator,
    gap_limit=10800,
) -> pd.Series:
    """
    Quality Code Check Data.

    Quality codes data based on the difference between the standard series and
    the check data

    Parameters
    ----------
    series : pd.Series
        Data to be quality coded
    check_series : pd.Series
        Check data
    qc_evaluator : data_sources.QualityCodeEvaluator
        Handler for QC comparisons
    gap_limit : integer (seconds)
        If the nearest real data point is more than this many seconds away, return 200

    Returns
    -------
    pd.Series
        The QC values of the series, indexed by the END time of the QC period
    """
    first_data_date = series.index[0]
    last_data_date = series.index[-1]
    if check_series.empty and isinstance(first_data_date, pd.Timestamp):
        # Maybe you should go find that check data
        warnings.warn("Warning: No check data", stacklevel=2)
        return pd.Series({first_data_date: np.NaN})
    first_check_date = check_series.index[0]
    last_check_date = check_series.index[-1]
    if (
        isinstance(first_data_date, pd.Timestamp)
        and isinstance(last_data_date, pd.Timestamp)
        and isinstance(first_check_date, pd.Timestamp)
        and isinstance(last_check_date, pd.Timestamp)
    ):
        qc_series = pd.Series({first_data_date: np.NaN})
        if first_check_date < first_data_date or last_check_date > last_data_date:
            # Can't check something that's not there
            raise KeyError(
                "Error: check data out of range. "
                f"First check date: {first_check_date}. "
                f"First data date: {first_data_date}. "
                f"Last check date: {last_check_date}. "
                f"Last data date: {last_data_date}. "
            )
        else:
            # Stuff actually working (hopefully)
            for check_time, check_value in check_series.items():
                if isinstance(check_time, pd.Timestamp):
                    adjusted_time = find_nearest_valid_time(series, check_time)
                    if abs((adjusted_time - check_time).total_seconds()) < gap_limit:
                        qc_value = qc_evaluator.find_qc(
                            series[adjusted_time], check_value
                        )
                    else:
                        qc_value = 200
                    qc_series[check_time] = qc_value
                else:
                    raise KeyError("Series indices should be pandas.Timestamp.")
            qc_series = qc_series.shift(-1, fill_value=0)
        return pd.Series(qc_series)
    else:
        raise KeyError("Series indices should be pandas.Timestamp.")


def missing_data_quality_code(series, qc_series, gap_limit):
    """
    Make sure that missing data is QC100.

    Returns qc_series with QC100 values added where series is NaN

    Parameters
    ----------
    series : pd.Series
        Base series which may contain NaNs
    qc_series
        QC series for base series without QC100 values
    gap_limit
        Maximum size of gaps which will be ignored

    Returns
    -------
    pd.Series
        The modified QC series, indexed by the start time of the QC period
    """
    for gap in gap_finder(series):
        if gap[1] > gap_limit:
            end_idx = series.index.get_loc(gap[0]) + gap[1]
            # end of gap should recover the value from previous
            if end_idx < len(series):
                prev_values = qc_series[qc_series.index <= series.index[end_idx]]
                prev_values = prev_values[prev_values > 100]
                prev_values = prev_values.sort_index()
                qc_series[series.index[end_idx]] = prev_values.iloc[-1]
                qc_series = qc_series.sort_index()

            # getting rid of any stray QC codes in the middle

            drop_series = qc_series
            drop_series = drop_series[drop_series.index > gap[0]]
            drop_series = drop_series[drop_series.index <= series.index[end_idx - 1]]
            qc_series = qc_series.drop(drop_series.index)

            # start of gap
            qc_series[gap[0]] = 100

    return qc_series.sort_index()


def find_nearest_time(series, dt):
    """
    Find the time in the series that is closest to dt.

    For example for the series::

        pd.Timestamp("2021-01-01 02:00"): 0.0,
        pd.Timestamp("2021-01-01 02:15"): 0.0,

    with dt::

        pd.Timestamp("2021-01-01 02:13"): 0.0,

    the result should be the closer ``pd.Timestamp("2021-01-01 02:15")`` value

    Parameters
    ----------
    series : pd.Series
        The series indexed by time

    dt : Datetime
        Time that may or may nor exactly line up with the series

    Returns
    -------
    Datetime
        The value of dt rounded to the nearest timestamp of the series

    """
    # Make sure it is in the range

    first_timestamp = series.index[0]
    last_timestamp = series.index[-1]
    if dt < first_timestamp or dt > last_timestamp:
        raise KeyError("Timestamp not within data range")

    output_index = series.index.get_indexer([dt], method="nearest")
    return series.index[output_index][0]


def find_nearest_valid_time(series, dt) -> pd.Timestamp:
    """
    Find the time in the series that is closest to dt, but ignoring NaN values (gaps).

    Parameters
    ----------
    series : pd.Series
        The series indexed by time
    dt : Datetime
        Time that may or may nor exactly line up with the series

    Returns
    -------
    Datetime
        The value of dt rounded to the nearest timestamp of the series

    """
    # Make sure it is in the range
    first_timestamp = series.index[0]
    last_timestamp = series.index[-1]
    if dt < first_timestamp or dt > last_timestamp:
        raise KeyError("Timestamp not within data range")

    series = series.dropna()
    output_index = series.index.get_indexer([dt], method="nearest")
    return series.index[output_index][0]


def base_data_qc_filter(base_series, qc_filter):
    """
    Filter out data based on quality code filter.

    Return only the base series data for which the next date in the qc_filter
    is 'true'

    Parameters
    ----------
    base_series : pandas.Series
        Data to be filtered
    qc_filter : pandas.Series of booleans
        Dates for which some condition is met or not

    Returns
    -------
    pandas.Series
        The filtered data

    """
    base_filter = qc_filter.reindex(base_series.index, method="ffill").fillna(False)
    return base_series[base_filter]


def base_data_meets_qc(base_series, qc_series, target_qc):
    """
    Find all data where QC targets are met.

    Returns only the base series data for which the next date in the qc_filter is
    equal to target_qc

    Parameters
    ----------
    base_series: pandas.Series
        Data to be filtered
    qc_series: pandas.Series
        quality code data series, some of which are presumably target_qc
    target_qc: int
        target quality code

    Returns
    -------
    pandas.Series
        Filtered data
    """
    return base_data_qc_filter(base_series, qc_series == target_qc)


def diagnose_data(base_series, check_series, qc_series, frequency):
    """
    Return description of how much missing data, how much for each QC, etc.

    This function feels like a mess, I'm sorry.
    The good news is that it is only a diagnostic, so feel free to change the hell
    out of it

    Parameters
    ----------
    raw_data : pandas.Series
        unprocessed base time series data
    base_series : pandas.Series
        processed base time series data
    check_series : pandas.Series
        Check datatime series
    qc_series : pandas.Series
        QC time series
    frequency : DateOffset or str
        Frequency to which the data gets set to

    Returns
    -------
    None
        Prints statements that describe the state of the data
    """
    # total time
    first_timestamp = base_series.index[0]
    last_timestamp = base_series.index[-1]
    total_time = last_timestamp - first_timestamp
    print(f"Time examined is {total_time} from {first_timestamp} to {last_timestamp}")
    print(
        f"Have check data for {check_series.index[-1] - first_timestamp} "
        f"(last check {check_series.index[-1]})"
    )

    # periods
    ave_period = pd.to_timedelta(frequency)  # total_time / (len(raw_data) - 1)
    gap_time = ave_period * (len(base_series) - len(base_series.dropna()) + 1)
    print(f"Missing {gap_time} of data, that's {gap_time/total_time*100}%")

    # QCs
    split_data = splitter(base_series, qc_series, frequency)
    for qc in split_data:
        print(
            f"Data that is QC{qc} makes up {len(split_data[qc].dropna()) / len(base_series.dropna()) * 100:.2f}% of "
            f"the "
            f"workable data and {len(split_data[qc].dropna()) / len(base_series) * 100:.2f}% of the time period"
        )


def splitter(base_series, qc_series, frequency):
    """
    Split the data up by QC code.

    Selects all data which meets a given QC code, pads the rest with NaN values
    Does this for all current NEMs values ([0, 100, 200, 300, 400, 500, 600])

    Parameters
    ----------
    base_series
        Time series data to be split up
    qc_series : pd.Series
        QC values to split the data by
    frequency : DateOffset or str
        Frequency to which the data gets set to

    Returns
    -------
    dict of int:pd.Series pairs
        Keys are the QC values as ints, values are series of data that fits
    """
    qc_list = [0, 100, 200, 300, 400, 500, 600]
    return_dict = {}
    for qc in qc_list:
        if qc == 100:
            return_dict[qc] = (
                base_data_meets_qc(base_series, qc_series, qc)
                .fillna(base_series.median())
                .asfreq(frequency)
            )
        else:
            return_dict[qc] = base_data_meets_qc(base_series, qc_series, qc).asfreq(
                frequency
            )

    return return_dict


def max_qc_limiter(qc_series: pd.Series, max_qc) -> pd.Series:
    """
    Enforce max_qc on a QC series.

    Replaces all values with QCs above max_qc with max_qc

    Parameters
    ----------
    qc_series : pd.Series
        The series to be limited.
    max_qc : numerical
        maximum allowed value. None imposes no limit.

    Returns
    -------
    pd.Series
        qc_series with too high QCs limited to max_qc
    """
    return pd.Series(qc_series.clip(np.NaN, max_qc))


def quality_encoder(
    base_series: pd.Series,
    check_series: pd.Series,
    qc_evaluator: QualityCodeEvaluator,
    gap_limit: int,
    max_qc=np.NaN,
) -> pd.Series:
    """
    Return complete QC series.

    Parameters
    ----------
    base_series : pd.Series
        Base time series data
    check_series : pd.Series
        Check data time series
    qc_evaluator : data_sources.QualityCodeEvaluator
        Handler for QC comparisons
    gap_limit
        Maximum size of gaps which will be ignored
    max_qc
        Maximum allowed QC value

    Returns
    -------
    pd.Series
        The modified QC series, indexed by the start time of the QC period
    """
    qc_series = check_data_quality_code(base_series, check_series, qc_evaluator)
    qc_series = missing_data_quality_code(base_series, qc_series, gap_limit=gap_limit)
    qc_series = max_qc_limiter(qc_series, max_qc)
    # qc_series.index.name = "Time"
    # qc_series.name = "Value"
    return qc_series
