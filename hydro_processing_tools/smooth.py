import numpy as np
import pandas as pd

def clip(
    unclipped,
    high_clip,
    low_clip
):
    """
    Clip values in a pandas Series within a specified range.

    Parameters:
    -----------
    unclipped : pandas.Series
        Input data to be clipped.

    high_clip : float
        Upper bound for clipping. Values greater than this will be set to NaN.

    low_clip : float
        Lower bound for clipping. Values less than this will be set to NaN.

    Returns:
    --------
    pandas.Series
        A Series containing the clipped values with the same index as the input Series.
    """
    print(unclipped.head())
    
    unclipped_arr = unclipped.values
    
    # Create a boolean condition for values that need to be clipped
    clip_cond = (unclipped_arr > high_clip) | (unclipped_arr < low_clip)
    
    # Use pandas' where function to clip values to NaN where the condition is True
    clipped_series = unclipped.where(~clip_cond, np.nan)
    print(type(clipped_series))
    
    return clipped_series
    

def fbewma(input_data, span):
    """
    Calculate the Forward-Backward Exponentially Weighted Moving Average (FB-EWMA) of a pandas Series.

    Parameters:
    -----------
    input_data : pandas.Series
        Input time series data to calculate the FB-EWMA on.

    span : int
        Span parameter for exponential weighting.

    Returns:
    --------
    pandas.Series
        A Series containing the FB-EWMA values with the same index as the input Series.
    """
    # Calculate the Forward EWMA.
    fwd = input_data.ewm(span=span).mean()
    
    # Calculate the Backward EWMA. (x[::-1] is the reverse of x)
    bwd = input_data[::-1].ewm(span=span).mean()
    
    # Stack fwd and the reverse of bwd on top of each other.
    stacked_ewma = pd.concat([fwd, bwd[::-1]])

    # Calculate the FB-EWMA by taking the mean between fwd and bwd.
    fb_ewma = stacked_ewma.groupby(level=0).mean()

    print(type(fb_ewma))
    return fb_ewma


def remove_outliers(input_data, span, delta):
    """
    Remove outliers from a time series by comparing it to the Forward-Backward Exponentially Weighted Moving Average (FB-EWMA).

    Parameters:
    -----------
    input_data : pandas.Series
        Input time series data.

    span : int
        Span parameter for exponential weighting used in the FB-EWMA.

    delta : float
        Threshold for identifying outliers. Values greater than this threshold will be set to NaN.

    Returns:
    --------
    pandas.Series
        A Series containing the time series with outliers removed with the same index as the input Series.
    """
    # Calculate the FB-EWMA of the time series
    fbewma_series = fbewma(input_data, span)
    
    # Create a condition to identify outliers based on the absolute difference between input_data and fbewma_series
    delta_cond = np.abs(input_data - fbewma_series) > delta

    # Set values to NaN where the condition is True
    gaps_series = input_data.where(~delta_cond, np.nan)

    print(type(gaps_series))
    return gaps_series


def remove_spikes(input_data, span, high_clip, low_clip, delta):
    """
    Remove spikes from a time series data using a combination of clipping and interpolation.

    Parameters:
    -----------
    input_data : pandas.Series
        Input time series data.

    span : int
        Span parameter for exponential weighting used in outlier detection.

    high_clip : float
        Upper bound for clipping. Values greater than this will be set to NaN.

    low_clip : float
        Lower bound for clipping. Values less than this will be set to NaN.

    delta : float
        Threshold for identifying outliers. Values greater than this threshold will be considered spikes.

    Returns:
    --------
    pandas.Series
        A Series containing the time series with spikes removed with the same index as the input Series.
    """
    # Clip values in the input data within the specified range
    clipped = clip(input_data, high_clip, low_clip)

    # Remove outliers using the remove_outliers function
    gaps_series = remove_outliers(input_data, span, delta)

    # Use pandas' .interpolate() on the Series
    interp_series = gaps_series.interpolate()
    
    print(type(interp_series))

    return interp_series
