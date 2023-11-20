"""Tools for displaying potentially problematic data."""
import matplotlib.pyplot as plt
import pandas as pd
import warnings
from hydrobot.evaluator import gap_finder, find_nearest_time


def gap_plotter(base_series, span=10):
    """
    Plot the areas around NaN values to check for invalid.

    :param base_series: pd.Series
        Data to have the gaps found and plotted
    :param span: int
        How many points around the gap gets plotted
    :return: None, but outputs a series of plots
    """
    for gap in gap_finder(base_series):
        plt.figure()
        idx = base_series.index.get_loc(gap[0])
        lower_idx = idx - span
        upper_idx = idx + span + gap[1]
        if lower_idx < 0:
            # below range
            upper_idx -= lower_idx
            lower_idx -= lower_idx
        if upper_idx > len(base_series):
            # above range
            lower_idx -= len(base_series) - upper_idx
            upper_idx -= len(base_series) - upper_idx
            if lower_idx < 0:
                # span is too big or not enough data
                warnings.warn("Warning: Span bigger than data")
                lower_idx = 0
        gap_range = base_series.iloc[lower_idx:upper_idx]
        plt.plot(gap_range.index, gap_range)
        plt.title(f"Gap starting at {gap[0]}")
    plt.show()


def check_plotter(base_series, check_series, span=10):
    """
    Plot the areas around check values to check for.

    :param base_series: pd.Series
        Data to plot
    :param check_series: pd.Series
        Check data which determines where the data is plotted
    :param span: int
    :return: None, but outputs a series of plots
    """
    for check in check_series:
        print(check)
        print(check_series[check])
        plt.figure()
        idx = base_series.index.get_loc(find_nearest_time(base_series, check))
        lower_idx = idx - span
        upper_idx = idx + span
        if lower_idx < 0:
            # below range
            upper_idx -= lower_idx
            lower_idx -= lower_idx
        if upper_idx > len(base_series):
            # above range
            lower_idx -= len(base_series) - upper_idx
            upper_idx -= len(base_series) - upper_idx
            if lower_idx < 0:
                # span is too big or not enough data
                warnings.warn("Warning: Span bigger than data")
                lower_idx = 0
        gap_range = base_series.iloc[lower_idx:upper_idx]
        plt.plot(gap_range.index, gap_range)
        plt.title(f"Check at {check}")
    plt.show()
