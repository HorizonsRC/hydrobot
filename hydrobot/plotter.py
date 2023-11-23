"""Tools for displaying potentially problematic data."""
import matplotlib.pyplot as plt
import pandas as pd
import warnings
from hydrobot.evaluator import gap_finder, find_nearest_time, splitter


def gap_plotter(base_series, span=20, show=True):
    """
    Plot the areas around NaN values to visually check for dodgy spike removal.

    Parameters
    ----------
    base_series : pd.Series
        Data to have the gaps found and plotted
    span : int
        How many points around the gap gets plotted
    show : bool
        Whether to show the plot directly when called

    Returns
    -------
    None
        Outputs a series of plots
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
    if show:
        plt.show()


def check_plotter(base_series, check_series, span=20, show=True):
    """
    Plot the areas around check values to visually check for dodgy data from inspections.

    Parameters
    ----------
    base_series : pd.Series
        Data to plot
    check_series : pd.Series
        Check data which determines where the data is plotted
    span : int
        How much space around the check data is shown
    show : bool
        Whether to show the plot directly when called

    Returns
    -------
    None
        Outputs a series of plots

    """
    for check in check_series.index:
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
        plt.plot(
            check,
            check_series[check],
            label="Check data",
            marker="o",
            color="black",
        )
        plt.title(f"Check at {check}")
    if show:
        plt.show()


def qc_colour(qc):
    """
    Give the colour of the QC.

    Parameters
    ----------
    qc : int
        Quality code

    Returns
    -------
    String
        Hex code for the colour of the QC
    """
    qc_dict = {
        0: "#9900ff",
        100: "#ff0000",
        200: "#8B5A00",
        300: "#d3d3d3",
        400: "#ffa500",
        500: "#00bfff",
        600: "#006400",
    }
    return qc_dict[qc]


def qc_plotter(base_series, check_series, qc_series, frequency, show=True):
    """
    Plot data with correct qc colour.

    Parameters
    ----------
    base_series : pd.Series
        Data to be sorted by colour
    check_series : pd.Series
        Check data to plot
    qc_series : pd.Series
        QC ranges for colour coding
    frequency : DateOffset or str
        Frequency to which the data gets set to
    show : bool
        Whether to show the plot directly when called

    Returns
    -------
    None
        Displays a plot
    """
    split_data = splitter(base_series, qc_series, frequency)
    plt.figure(figsize=(10, 6))
    for qc in split_data:
        plt.plot(
            split_data[qc].index,
            split_data[qc],
            label=f"QC{qc}",
            color=qc_colour(qc),
            marker=f"{'x' if qc==100 else ''}",
        )
    plt.plot(
        check_series.index,
        check_series,
        label="Check data",
        marker="o",
        color="black",
        linestyle="None",
    )

    plt.legend()
    if show:
        plt.show()
