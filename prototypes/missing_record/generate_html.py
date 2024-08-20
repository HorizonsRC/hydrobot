"""Generate pretty HTML report from the missing value csv file."""

import matplotlib
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from matplotlib import colors


def colormap_to_colorscale(cmap):
    """Transform matplotlib colormap into plotly colorscale."""
    return [colors.rgb2hex(cmap(k * 0.1)) for k in range(11)]


def colorscale_from_list(alist, name):
    """Define a colorscale from a list of colors."""
    cmap = colors.LinearSegmentedColormap.from_list(name, alist)
    colorscale = colormap_to_colorscale(cmap)
    return cmap, colorscale


def colorscale_from_array(array, bounds=None, cmap="jet"):
    """Define a colorscale from an array of values."""
    # Get the minimum and maximum values of the array

    if bounds is None:
        vmin = np.nanmin(array)
        vmax = np.nanmax(array)
    else:
        vmin, vmax = bounds
    # Convert mpl_cmap to plotly colorscale
    cmap = matplotlib.colormaps.get(cmap)

    # Define the normalizer
    norm = colors.Normalize(vmin=vmin, vmax=vmax)
    # Normalize the array
    normalized_array = norm(array)
    # Get the colors for the normalized array
    color_list = cmap(normalized_array)
    # Convert the colors to hex
    hex_colors = [colors.rgb2hex(color) for color in color_list]
    return hex_colors


if __name__ == "__main__":
    # Read the missing value csv file into pandas DataFrame
    # Columns of the dataframe are "Index, SiteName, [Measurement 1], [Measurement 2], ..."
    missing_values = pd.read_csv("output_dump/output.csv")
    print(missing_values.head())

    # Drop all rows that have NaN values in all columns except the first two columns
    missing_values = missing_values.dropna(
        axis=0, subset=missing_values.columns[1:], how="all"
    )
    print(missing_values.head())

    # Format all columns except first colomn as a timedelta object
    missing_values.loc[
        :,
        (missing_values.columns != "Index") & (missing_values.columns != "Sites"),
    ] = missing_values.loc[
        :,
        (missing_values.columns != "Index") & (missing_values.columns != "Sites"),
    ].astype(
        "timedelta64[s]", errors="ignore"
    )
    print(missing_values.head())

    # Get a 2D numpy array of all values except those from the first column
    values_only = missing_values.loc[
        :,
        (missing_values.columns != "Index") & (missing_values.columns != "Sites"),
    ]
    value_array = values_only.map(lambda x: x.total_seconds()).to_numpy()
    print(value_array)

    bounds = [0, 2e6]

    # Generate a colorscale from the values in the value_array
    colorscale = colorscale_from_array(value_array, bounds=bounds, cmap="inferno_r")
    full_colorscale = [["#ffffff"] * len(colorscale), colorscale]

    # Generate a plotly table from the DataFrame
    fig = go.Figure(
        data=[
            go.Table(
                header=dict(
                    values=list(missing_values.columns),
                    align="left",
                ),
                cells=dict(
                    values=[
                        missing_values[col].astype("str").to_numpy()
                        for col in missing_values.columns
                    ],
                    fill_color=full_colorscale,
                    font=dict(color=["grey"] * len(missing_values)),
                    align="left",
                ),
            )
        ]
    )

    # Generate static html report from the plotly table
    html_report = fig.to_html(full_html=False)

    # Output the html report to a file
    with open("output_dump/output.html", "w") as output_file:
        output_file.write(html_report)
