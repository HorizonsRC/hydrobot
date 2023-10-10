import numpy as np
import pandas as pd


def clip(
    unclipped,
    high_clip,
    low_clip
):
    """
    Clip values in an array within a specified range.

    Parameters:
    -----------
    unclipped : array-like
        Input data to be clipped.

    high_clip : float
        Upper bound for clipping. Values greater than this will be set to NaN.

    low_clip : float
        Lower bound for clipping. Values less than this will be set to NaN.

    Returns:
    --------
    array-like
        An array-like object containing the clipped values in the same type as the input.
    """
    # Convert input to a NumPy array for efficient element-wise operations
    unclipped_arr = np.array(unclipped) 
    print(unclipped_arr)
    print(high_clip)
    print(low_clip)
    
    # Create a boolean condition for values that need to be clipped
    clip_cond = (unclipped_arr > high_clip) & (unclipped_arr < low_clip)
    
    # Use NumPy's where function to clip values to NaN where the condition is True
    clipped_arr = np.where(clip_cond, np.nan, unclipped_arr)
    
    # Return the clipped values in the same type as the input
    if isinstance(unclipped, np.ndarray):
        return clipped_arr
    elif isinstance(unclipped, list):
        return clipped_arr.tolist()
    else:
        # Return as is if the input type is not recognized
        return clipped_arr
    

def fbewma(
    input_data,
    span
):
    """
    Calculate the Forward-Backward Exponentially Weighted Moving Average (FB-EWMA) of an array-like input data.

    Parameters:
    -----------
    input_data : array-like
        Input time series data to calculate the FB-EWMA on.

    span : int
        Span parameter for exponential weighting.

    Returns:
    --------
    array-like
        An array-like object containing the FB-EWMA values.
    """
    # Convert the input data to a NumPy array for efficient element-wise operations
    input_data_arr = np.array(input_data)

    # Calculate the Forward EWMA.
    fwd = pd.Series.ewm(input_data_arr, span=span).mean()
    
    # Calculate the Backward EWMA. (x[::-1] is the reverse of x)
    bwd = pd.Series.ewm(input_data_arr[::-1], span=span).mean()
    
    # Stack fwd and the reverse of bwd on top of each other.
    stacked_ewma = np.vstack((fwd, bwd[::-1]))

    # Calculate the FB-EWMA by taking the mean between fwd and bwd.
    fb_ewma = np.mean(stacked_ewma, axis=0)
    
    # Return the result as the same type as the input
    if isinstance(input_data, pd.Series):
        return pd.Series(fb_ewma)
    elif isinstance(input_data, np.ndarray):
        return fb_ewma
    else:
        return list(fb_ewma)


def remove_outliers(input_data, span, delta):
    """
    Remove outliers from a time series by comparing it to the Forward-Backward Exponentially Weighted Moving Average (FB-EWMA).

    Parameters:
    -----------
    input_data : array-like
        Input time series data.

    span : int
        Span parameter for exponential weighting used in the FB-EWMA.

    delta : float
        Threshold for identifying outliers. Values greater than this threshold will be set to NaN.

    Returns:
    --------
    array-like
        An array-like object containing the time series with outliers removed in the same type as the input.
    """
    # Convert the input time series to a NumPy array for efficient element-wise operations
    spikey_arr = np.array(input_data)

    # Calculate the FB-EWMA of the time series
    fbewma_arr = np.array(fbewma(input_data, span))

    # Create a condition to identify outliers based on the absolute difference between spikey_arr and fbewma_arr
    delta_cond = (np.abs(spikey_arr - fbewma_arr) > delta) 

    # Use NumPy's where function to set values to NaN where the condition is True
    gaps_arr = np.where(delta_cond, np.nan, spikey_arr)

    # Return the result in the same type as the input
    if isinstance(input_data, np.ndarray):
        return gaps_arr
    elif isinstance(input_data, list):
        return gaps_arr.tolist()
    else:
        # Return as is if the input type is not recognized
        return gaps_arr


def remove_spikes(
    input_data,
    span,
    high_clip,
    low_clip,
    delta,
):
    """
    Remove spikes from a time series data using a combination of clipping and interpolation.

    Parameters:
    -----------
    input_data : array-like
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
    array-like
        An array-like object containing the time series with spikes removed in the same type as the input.
    """
    # Clip values in the input data within the specified range
    clipped = clip(input_data, high_clip, low_clip)

    # Remove outliers using the remove_outliers function
    gaps_arr = remove_outliers(input_data, span, delta)

    # Create a pandas Series from the gaps_arr
    gaps_series = pd.Series(gaps_arr)

    # Use pandas' .interpolate() on the Series
    interp_series = gaps_series.interpolate()

    # Return the result in the same type as the input
    if isinstance(input_data, np.ndarray):
        return np.array(interp_series)
    elif isinstance(input_data, list):
        return interp_series.tolist()
    elif isinstance(input_data, pd.Series):
        return interp_series
    else:
        # Return as is if the input type is not recognized
        return interp_series
