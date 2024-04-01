"""Tools for displaying potentially problematic data."""
import warnings

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from hydrobot.evaluator import find_nearest_time, gap_finder, splitter
from hydrobot.utils import change_blocks, merge_all_comments


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
            color="darkturquoise",
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
        None: "darkslategrey",
        "nan": "darkslategrey",
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
        color="gray",
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
    None
        Displays a plot
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
                marker=dict(color="darkturquoise", size=10),
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
        color="black",
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
    None
        Displays a plot
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
            line=dict(color="black", dash="dash"),
        )
    )
    if show:
        fig.show()
    return fig


def make_processing_dash(
    fig,
    title,
    raw_standard_series,
    hilltop_standard_series,
    raw_check_series,
    prov_wq,
    inspections,
    ncrs,
):
    """Make the processing dash.

    Sorry about these docs I'm in a rush.
    """
    fig.add_trace(
        go.Scatter(
            x=raw_standard_series.index,
            y=raw_standard_series.to_numpy(),
            mode="lines",
            name="Raw data",
            line=dict(color="darkslategray", width=0.5),
            opacity=0.5,
        )
    )
    fig.add_trace(
        go.Scatter(
            x=raw_check_series.index,
            y=raw_check_series["Water Temperature Check"],
            mode="markers",
            name="Check data",
            marker=dict(color="darkturquoise", size=10),
        )
    )
    fig.add_trace(
        go.Scatter(
            x=prov_wq.index,
            y=prov_wq["Temp Check"],
            mode="markers",
            name="ProvWQ Check",
            marker=dict(color="darkslategray", size=10, symbol="square-open"),
        )
    )
    fig.add_trace(
        go.Scatter(
            x=inspections.index,
            y=inspections["Temp Check"],
            mode="markers",
            name="S123 Check",
            marker=dict(color="darkslategray", size=10, symbol="circle-open-dot"),
        )
    )
    fig.add_trace(
        go.Scatter(
            x=inspections.index,
            y=inspections["Temp Logger"],
            mode="markers",
            name="S123 Logger",
            marker=dict(color="darkslategray", size=10, symbol="x-thin-open"),
        )
    )
    fig_subplots = make_subplots(
        rows=3,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.02,
        specs=[
            [{"type": "scatter"}],
            [{"type": "scatter"}],
            [{"type": "table"}],
        ],
        row_heights=[0.4, 0.2, 0.4],
    )

    for trace in fig.data:
        fig_subplots.add_trace(trace, row=1, col=1)

    fig_subplots.update_layout(title=title)

    def find_nearest_periodic_indices(periodic_series, check_series):
        nearest_periodic_indices = []
        for check_index in check_series.index:
            # Calculate the difference between the check_index and every periodic index
            time_diff = np.abs(periodic_series.index - check_index)

            # Find the index in standard_series with the minimum time difference
            nearest_index = np.argmin(time_diff)

            nearest_periodic_indices.append(nearest_index)

        return nearest_periodic_indices

    nearest_check_indices = find_nearest_periodic_indices(
        hilltop_standard_series, raw_check_series["Water Temperature Check"]
    )

    nearest_prov_indices = find_nearest_periodic_indices(
        hilltop_standard_series, prov_wq
    )

    nearest_inspection_indices = find_nearest_periodic_indices(
        hilltop_standard_series, inspections
    )

    edited_blocks = change_blocks(raw_standard_series, hilltop_standard_series)

    first_change = True
    for change_start, change_end in edited_blocks:
        fig_subplots.add_vrect(
            x0=change_start,
            x1=change_end,
            showlegend=first_change,
            fillcolor="blue",
            opacity=0.25,
            line_width=0,
            name="Changes",
            row=1,
            col=1,
        )
        first_change = False

    fig_subplots.add_trace(
        go.Scatter(
            x=raw_check_series["Water Temperature Check"].index,
            y=hilltop_standard_series.iloc[nearest_check_indices].to_numpy()
            - raw_check_series["Water Temperature Check"].to_numpy(),
            mode="markers",
            name="Check data",
            marker=dict(color="darkturquoise", size=10, symbol="circle"),
            showlegend=False,
        ),
        row=2,
        col=1,
    )

    fig_subplots.add_trace(
        go.Scatter(
            x=hilltop_standard_series.iloc[nearest_check_indices].index,
            y=hilltop_standard_series.iloc[nearest_check_indices].to_numpy()
            - raw_check_series["Water Temperature Check"].to_numpy(),
            mode="markers",
            name="Check Align",
            marker=dict(color="darkturquoise", size=10, symbol="circle"),
            showlegend=False,
            opacity=0.5,
            hoverinfo="skip",
        ),
        row=2,
        col=1,
    )
    arrow_annotations = []
    for stand, check in zip(
        hilltop_standard_series.iloc[nearest_check_indices].items(),
        raw_check_series["Water Temperature Check"].items(),
        strict=True,
    ):
        # If the timestamps are not the same
        if stand[0] != check[0]:
            arrow_annotations.append(
                dict(
                    ax=check[0],
                    ay=stand[1] - check[1],
                    x=stand[0],
                    y=stand[1] - check[1],
                    axref="x2",
                    ayref="y2",
                    xref="x2",
                    yref="y2",
                    arrowhead=2,
                    arrowcolor="darkturquoise",
                    showarrow=True,
                    opacity=0.5,
                    standoff=6,
                )
            )

    fig_subplots.add_trace(
        go.Scatter(
            x=prov_wq.index,
            y=hilltop_standard_series.iloc[nearest_prov_indices].to_numpy()
            - prov_wq["Temp Check"].to_numpy(),
            mode="markers",
            name="ProvWQ Check",
            marker=dict(color="darkslategray", size=10, symbol="square-open"),
            showlegend=False,
        ),
        row=2,
        col=1,
    )
    fig_subplots.add_trace(
        go.Scatter(
            x=hilltop_standard_series.iloc[nearest_prov_indices].index,
            y=hilltop_standard_series.iloc[nearest_prov_indices].to_numpy()
            - prov_wq["Temp Check"].to_numpy(),
            mode="markers",
            name="ProvWQ Align",
            marker=dict(color="darkslategray", size=10, symbol="square-open"),
            showlegend=False,
            opacity=0.5,
            hoverinfo="skip",
        ),
        row=2,
        col=1,
    )
    for stand, prov in zip(
        hilltop_standard_series.iloc[nearest_prov_indices].items(),
        prov_wq.iterrows(),
        strict=True,
    ):
        # If the timestamps are not the same
        if stand[0] != prov[0]:
            arrow_annotations.append(
                dict(
                    ax=prov[0],
                    ay=stand[1] - prov[1]["Temp Check"],
                    x=stand[0],
                    y=stand[1] - prov[1]["Temp Check"],
                    axref="x2",
                    ayref="y2",
                    xref="x2",
                    yref="y2",
                    arrowhead=2,
                    arrowcolor="darkslategray",
                    showarrow=True,
                    opacity=0.5,
                    standoff=6,
                )
            )

    fig_subplots.add_trace(
        go.Scatter(
            x=inspections.index,
            y=hilltop_standard_series.iloc[nearest_inspection_indices].to_numpy()
            - inspections["Temp Check"].to_numpy(),
            mode="markers",
            name="S123 Check",
            marker=dict(color="darkslategray", size=10, symbol="circle-open-dot"),
            showlegend=False,
        ),
        row=2,
        col=1,
    )

    fig_subplots.add_trace(
        go.Scatter(
            x=hilltop_standard_series.iloc[nearest_inspection_indices].index,
            y=hilltop_standard_series.iloc[nearest_inspection_indices].to_numpy()
            - inspections["Temp Check"].to_numpy(),
            mode="markers",
            name="S123 Check Aligned",
            marker=dict(color="darkslategray", size=10, symbol="circle-open-dot"),
            showlegend=False,
            opacity=0.5,
            hoverinfo="skip",
        ),
        row=2,
        col=1,
    )

    for stand, insp in zip(
        hilltop_standard_series.iloc[nearest_inspection_indices].items(),
        inspections.iterrows(),
        strict=True,
    ):
        # If the timestamps are not the same
        if stand[0] != insp[0] and not pd.isna(insp[1]["Temp Logger"]):
            arrow_annotations.append(
                dict(
                    ax=insp[0],
                    ay=stand[1] - insp[1]["Temp Check"],
                    x=stand[0],
                    y=stand[1] - insp[1]["Temp Check"],
                    axref="x2",
                    ayref="y2",
                    xref="x2",
                    yref="y2",
                    arrowhead=2,
                    arrowcolor="darkslategray",
                    showarrow=True,
                    opacity=0.5,
                    standoff=6,
                )
            )

    fig_subplots.add_trace(
        go.Scatter(
            x=inspections.index,
            y=hilltop_standard_series.iloc[nearest_inspection_indices].to_numpy()
            - inspections["Temp Logger"].to_numpy(),
            mode="markers",
            name="S123 Logger",
            marker=dict(color="darkslategray", size=10, symbol="x-thin-open"),
            showlegend=False,
        ),
        row=2,
        col=1,
    )

    fig_subplots.add_trace(
        go.Scatter(
            x=hilltop_standard_series.iloc[nearest_inspection_indices].index,
            y=hilltop_standard_series.iloc[nearest_inspection_indices].to_numpy()
            - inspections["Temp Logger"].to_numpy(),
            mode="markers",
            name="S123 Logger Aligned",
            marker=dict(color="darkslategray", size=10, symbol="x-thin-open"),
            showlegend=False,
            opacity=0.5,
            hoverinfo="skip",
        ),
        row=2,
        col=1,
    )

    for stand, insp in zip(
        hilltop_standard_series.iloc[nearest_inspection_indices].items(),
        inspections.iterrows(),
        strict=True,
    ):
        # If the timestamps are not the same
        if stand[0] != insp[0] and not pd.isna(insp[1]["Temp Logger"]):
            arrow_annotations.append(
                dict(
                    ax=insp[0],
                    ay=stand[1] - insp[1]["Temp Logger"],
                    x=stand[0],
                    y=stand[1] - insp[1]["Temp Logger"],
                    axref="x2",
                    ayref="y2",
                    xref="x2",
                    yref="y2",
                    arrowhead=2,
                    arrowcolor="darkslategray",
                    showarrow=True,
                    opacity=0.5,
                    standoff=6,
                )
            )

    fig_subplots.update_layout(annotations=arrow_annotations)

    qc400 = 1.2
    qc500 = 0.8

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

    all_comments = merge_all_comments(raw_check_series, prov_wq, inspections, ncrs)

    fig_subplots.add_trace(
        go.Table(
            columnwidth=[1, 3, 1],
            header=dict(
                values=list(all_comments.columns),
                align="left",
            ),
            cells=dict(
                values=[all_comments[cn] for cn in all_comments.columns],
                align="left",
            ),
        ),
        row=3,
        col=1,
    )

    fig_subplots.update_layout(
        hovermode="x unified",
    )

    return fig_subplots
