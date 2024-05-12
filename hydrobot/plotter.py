"""Tools for displaying potentially problematic data."""
import warnings

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from hydrobot.evaluator import find_nearest_time, gap_finder, splitter
from hydrobot.utils import change_blocks


def gap_plotter(base_series, span=20, show=True):
    """Plot the areas around NaN.to_numpy() to visually check for dodgy spike removal.

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
                warnings.warn("Warning: Span bigger than data", stacklevel=2)
                lower_idx = 0
        gap_range = base_series.iloc[lower_idx:upper_idx]
        plt.plot(gap_range.index, gap_range)
        plt.title(f"Gap starting at {gap[0]}")
    if show:
        plt.show()


def check_plotter(base_series, check_series, span=20, show=True):
    """Plot the areas around check.to_numpy() to visually check for dodgy data from inspections.

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
                warnings.warn("Warning: Span bigger than data", stacklevel=2)
                lower_idx = 0
        gap_range = base_series.iloc[lower_idx:upper_idx]
        plt.plot(gap_range.index, gap_range)
        plt.plot(
            check,
            check_series[check],
            label="Check data",
            marker="o",
            color="darkcyan",
        )
        plt.title(f"Check at {check}")
    if show:
        plt.show()


def qc_colour(qc):
    """Give the colour of the QC.

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


def qc_plotter(base_series, check_series, qc_series, frequency, show=True):
    """Plot data with correct qc colour.

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
    plt.figure()
    for qc in split_data:
        plt.plot(
            split_data[qc].index,
            split_data[qc],
            label=f"QC{qc}",
            color=qc_colour(qc),
            marker=f"{'x' if qc==100 else '.'}",
        )
    plt.plot(
        check_series.index,
        check_series,
        label="Check data",
        marker="o",
        color="darkgray",
        linestyle="None",
    )
    plt.xticks(rotation=45, ha="right")

    plt.legend()
    if show:
        plt.show()


def qc_plotter_plotly(
    base_series, check_series, qc_series, frequency, show=True, **kwargs
):
    """Plot data with correct qc colour.

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
    go.Figure

    """
    split_data = splitter(base_series, qc_series, frequency)
    fig = go.Figure()
    for qc in split_data:
        fig.add_trace(
            go.Scatter(
                x=split_data[qc].index,
                y=split_data[qc],
                mode="lines",
                name=f"QC{qc}",
                line=dict(color=qc_colour(qc)),
            )
        )
    if check_series is not None:
        fig.add_trace(
            go.Scatter(
                x=check_series.index,
                y=check_series,
                mode="markers",
                name="Check data",
                marker=dict(color="darkcyan", size=10),
            )
        )
    fig.update_layout(
        title="Quality Control Plot",
        xaxis=dict(title="Date"),
        yaxis=dict(title="Value"),
        legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01),
        xaxis_tickangle=-45,
        **kwargs,
    )
    if show:
        fig.show()
    return fig


def comparison_qc_plotter(
    base_series, raw_series, check_series, qc_series, frequency, show=True
):
    """Plot data with correct qc colour a la qc_plotter(), and the raw data overlaid.

    Parameters
    ----------
    base_series : pd.Series
        Data to be sorted by colour
    raw_series : pd.Series
        Data that has not been processed
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
    qc_plotter(base_series, check_series, qc_series, frequency, show=False)
    plt.plot(
        raw_series.index,
        raw_series,
        label="Raw data",
        color="darkgray",
        marker="",
        linestyle="dashed",
    )
    plt.legend()
    if show:
        plt.show()


def comparison_qc_plotter_plotly(
    base_series,
    raw_series,
    check_series,
    qc_series,
    frequency,
    show=True,
    **kwargs,
):
    """Plot data with correct qc colour a la qc_plotter(), and the raw data overlaid.

    Parameters
    ----------
    base_series : pd.Series
        Data to be sorted by colour
    raw_series : pd.Series
        Data that has not been processed
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
    comparison_qc_plotter_plotly
    """
    fig = qc_plotter_plotly(
        base_series, check_series, qc_series, frequency, show=False, **kwargs
    )

    fig.add_trace(
        go.Scatter(
            x=raw_series.index,
            y=raw_series,
            mode="lines",
            name="Raw data",
            line=dict(color="darkgray", dash="dash"),
        )
    )
    if show:
        fig.show()
    return fig


def make_processing_dash(fig, processor, check_data):
    """Make the processing dash.

    Sorry about these docs I'm in a rush.
    """
    standard_data = processor.standard_data
    check_data["Value"] += processor.quality_code_evaluator.constant_check_shift

    htp_check = check_data[check_data["Source"] == "HTP"]
    srv_check = check_data[check_data["Source"] == "INS"]
    pwq_check = check_data[check_data["Source"] == "SOE"]
    fig.add_trace(
        go.Scatter(
            x=standard_data["Raw"].index,
            y=standard_data["Raw"].to_numpy(),
            mode="lines",
            name="Raw data",
            line=dict(color="darkgray", width=0.5),
            opacity=0.5,
        )
    )
    fig.add_trace(
        go.Scatter(
            x=htp_check.index,
            y=htp_check["Value"],
            mode="markers",
            name="Check data",
            marker=dict(color="darkcyan", size=10),
        )
    )
    fig.add_trace(
        go.Scatter(
            x=pwq_check.index,
            y=pwq_check["Value"],
            mode="markers",
            name="ProvWQ Check",
            marker=dict(color="darkgray", size=10, symbol="square-open"),
        )
    )
    fig.add_trace(
        go.Scatter(
            x=srv_check.index,
            y=srv_check["Value"],
            mode="markers",
            name="S123 Check",
            marker=dict(color="darkgray", size=10, symbol="circle-open-dot"),
        )
    )
    fig.add_trace(
        go.Scatter(
            x=srv_check.index,
            y=srv_check["Logger"],
            mode="markers",
            name="S123 Logger",
            marker=dict(color="darkgray", size=10, symbol="x-thin-open"),
        )
    )
    fig_subplots = make_subplots(
        rows=2,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.02,
        specs=[
            [{"type": "scatter"}],
            [{"type": "scatter"}],
        ],
        row_heights=[0.7, 0.3],
    )

    for trace in fig.data:
        fig_subplots.add_trace(trace, row=1, col=1)

    fig_subplots.update_layout(title=processor.site)

    def find_nearest_periodic_indices(periodic_series, check_series):
        nearest_periodic_indices = []
        for check_index in check_series.index:
            # Calculate the difference between the check_index and every periodic index
            time_diff = np.abs(periodic_series.index - check_index)

            # Find the index in standard_series with the minimum time difference
            nearest_index = np.argmin(time_diff)

            nearest_periodic_indices.append(nearest_index)

        return nearest_periodic_indices

    nearest_htp_indices = find_nearest_periodic_indices(standard_data, htp_check)

    nearest_pwq_indices = find_nearest_periodic_indices(standard_data, pwq_check)

    nearest_srv_indices = find_nearest_periodic_indices(standard_data, srv_check)

    edited_blocks = change_blocks(standard_data["Raw"], standard_data["Value"])

    first_change = True
    for change_start, change_end in edited_blocks:
        fig_subplots.add_vrect(
            x0=change_start,
            x1=change_end,
            showlegend=first_change,
            fillcolor="teal",
            opacity=0.25,
            line_width=0,
            name="Changes",
            row=1,
            col=1,
        )
        first_change = False

    fig_subplots.add_trace(
        go.Scatter(
            x=htp_check["Value"].index,
            y=htp_check["Value"].to_numpy()
            - standard_data["Value"].iloc[nearest_htp_indices].to_numpy(),
            mode="markers",
            name="Check data",
            marker=dict(color="darkcyan", size=10, symbol="circle"),
            showlegend=False,
        ),
        row=2,
        col=1,
    )

    fig_subplots.add_trace(
        go.Scatter(
            x=standard_data["Value"].iloc[nearest_htp_indices].index,
            y=htp_check["Value"].to_numpy()
            - standard_data["Value"].iloc[nearest_htp_indices].to_numpy(),
            mode="markers",
            name="Check Align",
            marker=dict(color="darkcyan", size=10, symbol="circle"),
            showlegend=False,
            opacity=0.5,
            hoverinfo="skip",
        ),
        row=2,
        col=1,
    )
    arrow_annotations = []
    for stand, check in zip(
        standard_data["Value"].iloc[nearest_htp_indices].items(),
        htp_check["Value"].items(),
        strict=True,
    ):
        # If the timestamps are not the same
        if stand[0] != check[0] and not pd.isna(check[1]):
            arrow_annotations.append(
                dict(
                    ax=check[0],
                    ay=check[1] - stand[1],
                    x=stand[0],
                    y=check[1] - stand[1],
                    axref="x2",
                    ayref="y2",
                    xref="x2",
                    yref="y2",
                    arrowhead=2,
                    arrowcolor="darkcyan",
                    showarrow=True,
                    opacity=0.5,
                    standoff=6,
                )
            )

    fig_subplots.add_trace(
        go.Scatter(
            x=pwq_check.index,
            y=pwq_check["Value"].to_numpy()
            - standard_data["Value"].iloc[nearest_pwq_indices].to_numpy(),
            mode="markers",
            name="ProvWQ Check",
            marker=dict(color="darkgray", size=10, symbol="square-open"),
            showlegend=False,
        ),
        row=2,
        col=1,
    )
    fig_subplots.add_trace(
        go.Scatter(
            x=standard_data["Value"].iloc[nearest_pwq_indices].index,
            y=pwq_check["Value"].to_numpy()
            - standard_data["Value"].iloc[nearest_pwq_indices].to_numpy(),
            mode="markers",
            name="ProvWQ Align",
            marker=dict(color="darkgray", size=10, symbol="square-open"),
            showlegend=False,
            opacity=0.5,
            hoverinfo="skip",
        ),
        row=2,
        col=1,
    )
    for stand, prov in zip(
        standard_data["Value"].iloc[nearest_pwq_indices].items(),
        pwq_check.iterrows(),
        strict=True,
    ):
        # If the timestamps are not the same
        if stand[0] != prov[0] and not pd.isna(prov[1]["Value"]):
            arrow_annotations.append(
                dict(
                    ax=prov[0],
                    ay=prov[1]["Value"] - stand[1],
                    x=stand[0],
                    y=prov[1]["Value"] - stand[1],
                    axref="x2",
                    ayref="y2",
                    xref="x2",
                    yref="y2",
                    arrowhead=2,
                    arrowcolor="darkgray",
                    showarrow=True,
                    opacity=0.5,
                    standoff=6,
                )
            )

    fig_subplots.add_trace(
        go.Scatter(
            x=srv_check.index,
            y=srv_check["Value"].to_numpy()
            - standard_data["Value"].iloc[nearest_srv_indices].to_numpy(),
            mode="markers",
            name="S123 Check",
            marker=dict(color="darkgray", size=10, symbol="circle-open-dot"),
            showlegend=False,
        ),
        row=2,
        col=1,
    )

    fig_subplots.add_trace(
        go.Scatter(
            x=standard_data["Value"].iloc[nearest_srv_indices].index,
            y=srv_check["Value"].to_numpy()
            - standard_data["Value"].iloc[nearest_srv_indices].to_numpy(),
            mode="markers",
            name="S123 Check Aligned",
            marker=dict(color="darkgray", size=10, symbol="circle-open-dot"),
            showlegend=False,
            opacity=0.5,
            hoverinfo="skip",
        ),
        row=2,
        col=1,
    )

    for stand, insp in zip(
        standard_data["Value"].iloc[nearest_srv_indices].items(),
        srv_check.iterrows(),
        strict=True,
    ):
        # If the timestamps are not the same
        if stand[0] != insp[0] and not pd.isna(insp[1]["Logger"]):
            arrow_annotations.append(
                dict(
                    ax=insp[0],
                    ay=insp[1]["Value"] - stand[1],
                    x=stand[0],
                    y=insp[1]["Value"] - stand[1],
                    axref="x2",
                    ayref="y2",
                    xref="x2",
                    yref="y2",
                    arrowhead=2,
                    arrowcolor="darkgray",
                    showarrow=True,
                    opacity=0.5,
                    standoff=6,
                )
            )

    fig_subplots.add_trace(
        go.Scatter(
            x=srv_check.index,
            y=srv_check["Logger"].to_numpy()
            - standard_data["Value"].iloc[nearest_srv_indices].to_numpy(),
            mode="markers",
            name="S123 Logger",
            marker=dict(color="darkgray", size=10, symbol="x-thin-open"),
            showlegend=False,
        ),
        row=2,
        col=1,
    )

    fig_subplots.add_trace(
        go.Scatter(
            x=standard_data["Value"].iloc[nearest_srv_indices].index,
            y=srv_check["Logger"].to_numpy()
            - standard_data["Value"].iloc[nearest_srv_indices].to_numpy(),
            mode="markers",
            name="S123 Logger Aligned",
            marker=dict(color="darkgray", size=10, symbol="x-thin-open"),
            showlegend=False,
            opacity=0.5,
            hoverinfo="skip",
        ),
        row=2,
        col=1,
    )

    for stand, insp in zip(
        standard_data["Value"].iloc[nearest_srv_indices].items(),
        srv_check.iterrows(),
        strict=True,
    ):
        # If the timestamps are not the same
        if stand[0] != insp[0] and not pd.isna(insp[1]["Logger"]):
            arrow_annotations.append(
                dict(
                    ax=insp[0],
                    ay=insp[1]["Logger"] - stand[1],
                    x=stand[0],
                    y=insp[1]["Logger"] - stand[1],
                    axref="x2",
                    ayref="y2",
                    xref="x2",
                    yref="y2",
                    arrowhead=2,
                    arrowcolor="darkgray",
                    showarrow=True,
                    opacity=0.5,
                    standoff=6,
                )
            )

    fig_subplots.update_layout(annotations=arrow_annotations)

    qc400 = processor.quality_code_evaluator.qc_500_limit
    qc500 = processor.quality_code_evaluator.qc_600_limit

    fig_subplots.add_hline(
        y=qc400,
        line=dict(color="#ffa500", width=1, dash="dash"),
        name="QC400",
        row=2,
        col=1,
        showlegend=True,
        legendgroup="QC400",
    )

    fig_subplots.add_hline(
        y=-qc400,
        line=dict(color="#ffa500", width=1, dash="dash"),
        name="QC400",
        row=2,
        col=1,
        showlegend=False,
        legendgroup="QC400",
        visible=True,
    )
    fig_subplots.add_hline(
        y=qc500,
        line=dict(color="#00bfff", width=1, dash="dash"),
        name="QC500",
        row=2,
        col=1,
        showlegend=True,
        legendgroup="QC500",
        visible=True,
    )
    fig_subplots.add_hline(
        y=-qc500,
        line=dict(color="#00bfff", width=1, dash="dash"),
        name="QC500",
        row=2,
        col=1,
        showlegend=False,
        legendgroup="QC500",
        visible=True,
    )

    fig_subplots.update_layout(
        hovermode="x unified",
    )

    return fig_subplots
