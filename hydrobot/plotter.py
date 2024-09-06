"""Tools for displaying potentially problematic data."""

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from hydrobot.evaluator import splitter


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
        None: "darkgray",
        "nan": "darkgray",
        0: "#9900ff",
        100: "#ff0000",
        200: "#8B5A00",
        300: "#d3d3d3",
        400: "#ffa500",
        500: "#00bfff",
        600: "#006400",
    }
    return qc_dict[qc]


def plot_raw_data(standard_data, fig=None, **kwargs: int):
    """
    Plot the raw data with a grey line.

    Parameters
    ----------
    standard_data : pd.Series
        The data to be plotted. Needs to have a "Raw" column.
    fig : go.Figure
        The figure to add the plot to
    kwargs : dict
        Additional arguments to be passed to the plot

    Returns
    -------
    go.Figure
    """
    if fig is None:
        fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=standard_data["Raw"].index,
            y=standard_data["Raw"].to_numpy(),
            mode="lines",
            name="Raw data",
            line=dict(color="darkgray", width=0.5),
            opacity=0.5,
        ),
        **kwargs,
    )
    return fig


def plot_qc_codes(
    standard_series,
    quality_series,
    fig=None,
    **kwargs,
):
    """Plot data with correct qc colour.

    Parameters
    ----------
    standard_series : pd.Series
        Data to be sorted by colour
    quality_series : pd.Series
        Data to use to determine colour
    fig : go.Figure | None, optional
        The figure to add info to, will make a figure if None

    Returns
    -------
    go.Figure

    """
    split_data = splitter(standard_series, quality_series)
    if fig is None:
        fig = go.Figure()
    for qc in split_data:
        fig.add_trace(
            go.Scatter(
                x=standard_series.index,
                y=split_data[qc].reindex(standard_series.index),
                mode="lines",
                name=f"QC{qc}",
                line=dict(color=qc_colour(qc)),
            ),
            **kwargs,
        )
    return fig


check_colours = [
    "darkcyan",
    "darkgray",
    "darkgray",
    "darkgray",
    "darkgray",
    "darkgray",
]
check_markers = [
    "circle",
    "square-open",
    "circle-open-dot",
    "x-thin-open",
    "star-triangle-up-open",
    "star-triangle-down-open",
]


def add_qc_limit_bars(
    qc400,
    qc500,
    fig=None,
    **kwargs: int,
):
    """
    Add horizontal lines to the plot for the QC limits.

    Parameters
    ----------
    qc400 : float
        The value of the QC400 limit
    qc500 : float
        The value of the QC500 limit
    fig : go.Figure
        The figure to add the horizontal lines to
    kwargs : dict
        Additional arguments to pass to the lines

    Returns
    -------
    go.Figure
    """
    if fig is None:
        fig = go.Figure()
    fig.add_hline(
        y=qc400,
        line=dict(color="#ffa500", width=1, dash="dash"),
        name="QC400",
        showlegend=True,
        legendgroup="QC400",
        **kwargs,
    )

    fig.add_hline(
        y=-qc400,
        line=dict(color="#ffa500", width=1, dash="dash"),
        name="QC400",
        showlegend=False,
        legendgroup="QC400",
        visible=True,
        **kwargs,
    )
    fig.add_hline(
        y=qc500,
        line=dict(color="#00bfff", width=1, dash="dash"),
        name="QC500",
        showlegend=True,
        legendgroup="QC500",
        visible=True,
        **kwargs,
    )
    fig.add_hline(
        y=-qc500,
        line=dict(color="#00bfff", width=1, dash="dash"),
        name="QC500",
        showlegend=False,
        legendgroup="QC500",
        visible=True,
        **kwargs,
    )

    fig.update_layout(
        hovermode="x unified",
    )

    return fig


def find_nearest_periodic_indices(periodic_series, check_series):
    """Find the nearest periodic timestamp.

    Given a periodic and non-periodic series, this function finds the indices of
    the periodic series that is closest to the points in the non-periodic series.

    Parameters
    ----------
    periodic_series : pd.Series
        The series that has periodic timestamps
    check_series : pd.Series
        The series that does not have periodic timestamps

    Returns
    -------
    list[int]
        A list of indices of the periodic series that are closest to the check series

    """
    nearest_periodic_indices = []
    for check_index in check_series.index:
        # Calculate the difference between the check_index and every periodic index
        time_diff = np.abs(periodic_series.index - check_index)

        # Find the index in standard_series with the minimum time difference
        nearest_index = np.argmin(time_diff)

        nearest_periodic_indices.append(nearest_index)

    return nearest_periodic_indices


def plot_check_data(
    standard_data,
    check_data,
    constant_check_shift,
    tag_list=None,
    check_names=None,
    ghosts=False,
    diffs=False,
    align_checks=False,
    fig=None,
    **kwargs: int,
):
    """
    Plot the check data.

    Parameters
    ----------
    standard_data : pd.Series
        The data to be plotted
    check_data : pd.Series
        The data to be plotted on top of the standard data
    constant_check_shift : float
        The shift between the check data and the standard data
    tag_list : list[str]
        The tags of the check data
    check_names : list[str]
        The names of the check data
    ghosts : bool
        Whether to plot the check data where the timestamps are
    diffs : bool
        Whether to plot the difference between the check data and the standard data
    align_checks : bool
        Whether to align the check data to the standard data
    fig : go.Figure
        The figure to add the plot to
    kwargs : dict
        Additional arguments to be passed to the plot

    Returns
    -------
    go.Figure


    """
    if fig is None:
        fig = go.Figure()
    if tag_list is None:
        tag_list = list(set(check_data["Source"]))
    if check_names is None:
        check_names = tag_list

    check_data["Value"] += constant_check_shift

    arrow_annotations = []

    for i, tag in enumerate(tag_list):
        tag_check = check_data[check_data["Source"] == tag]
        if align_checks or ghosts or diffs:
            nearest_standards = find_nearest_periodic_indices(standard_data, tag_check)
            standards = standard_data["Value"].iloc[nearest_standards]
            timestamps = standards.index
        else:
            timestamps = tag_check.index
        if diffs:
            checks = (
                tag_check["Value"].to_numpy() - standard_data["Value"].loc[timestamps]
            )
        else:
            checks = tag_check["Value"].to_numpy()

        fig.add_trace(
            go.Scatter(
                x=timestamps,
                y=checks,
                mode="markers",
                name=check_names[i],
                marker=dict(color=check_colours[i], size=10, symbol=check_markers[i]),
            ),
            **kwargs,
        )
        if ghosts:
            # Add check data where they actually are
            fig.add_trace(
                go.Scatter(
                    x=tag_check.index,
                    y=checks,
                    mode="markers",
                    name=check_names[i] + " Ghost",
                    marker=dict(
                        color=check_colours[i],
                        size=10,
                        symbol=check_markers[i],
                    ),
                    showlegend=False,
                    opacity=0.5,
                    hoverinfo="skip",
                ),
                **kwargs,
            )

            # Add arrows that point from where check is to where it is used
            for old_stamp, shift_stamp, check_value in zip(
                tag_check.index,
                timestamps,
                checks,
                strict=True,
            ):
                # If the timestamps are not the same
                if shift_stamp != old_stamp and not pd.isna(check_value):
                    arrow_annotations.append(
                        dict(
                            ax=old_stamp,
                            ay=check_value,
                            x=shift_stamp,
                            y=check_value,
                            axref="x",
                            ayref="y",
                            xref="x",
                            yref="y",
                            arrowhead=2,
                            arrowcolor=check_colours[i],
                            showarrow=True,
                            opacity=0.5,
                            standoff=6,
                        )
                    )
    fig.update_layout(annotations=arrow_annotations)
    return fig


def plot_processing_overview_chart(
    standard_data,
    quality_data,
    check_data,
    constant_check_shift,
    qc_500_limit,
    qc_600_limit,
    tag_list=None,
    check_names=None,
    fig=None,
    **kwargs,
):
    """
    Plot the standard processing plot with small pcc chart underneath.

    Parameters
    ----------
    standard_data : pd.Series
        The data to be plotted
    quality_data : pd.Series
        The quality data to be plotted
    check_data : pd.Series
        The check data to be plotted
    constant_check_shift : float
        The shift between the check data and the standard data
    qc_500_limit : float
        The value of the QC500 limit
    qc_600_limit : float
        The value of the QC600 limit
    tag_list : list[str]
        The tags of the check data
    check_names : list[str]
        The names of the check data
    fig : go.Figure, optional
        The figure to add the plot to, will make a new one if none
    kwargs : dict
        Additional arguments to pass to the plot

    Returns
    -------
    go.Figure
    """
    if tag_list is None:
        tag_list = list(set(check_data["Source"]))
    if check_names is None:
        check_names = tag_list

    fig = make_subplots(
        rows=2,
        cols=1,
        shared_xaxes=True,
        row_heights=(0.7, 0.3),
        vertical_spacing=0.02,
        figure=fig,
    )

    fig = plot_raw_data(standard_data, fig=fig, row=1, col=1)
    fig = plot_qc_codes(
        standard_data["Value"],
        quality_data["Value"],
        fig=fig,
        row=1,
        col=1,
        **kwargs,
    )

    fig = plot_check_data(
        standard_data,
        check_data,
        constant_check_shift,
        tag_list=tag_list,
        check_names=check_names,
        ghosts=True,
        fig=fig,
        row=1,
        col=1,
        **kwargs,
    )

    fig = plot_check_data(
        standard_data,
        check_data,
        constant_check_shift,
        tag_list=tag_list,
        check_names=check_names,
        ghosts=True,
        diffs=True,
        fig=fig,
        row=2,
        col=1,
        **kwargs,
    )

    #
    fig = add_qc_limit_bars(
        qc_500_limit,
        qc_600_limit,
        fig=fig,
        row=2,
        col=1,
        **kwargs,
    )

    fig.update_yaxes(autorange=True)

    return fig
