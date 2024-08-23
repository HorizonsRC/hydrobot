"""Generate pretty HTML report from the missing value csv file."""

import matplotlib
import numpy as np
import pandas as pd
from matplotlib import colors


def colormap_to_colorscale(cmap):
    """Transform matplotlib colormap into plotly colorscale."""
    return [colors.rgb2hex(cmap(k * 0.1)) for k in range(11)]


def colorscale_from_list(alist, name):
    """Define a colorscale from a list of colors."""
    cmap = colors.LinearSegmentedColormap.from_list(name, alist)
    colorscale = colormap_to_colorscale(cmap)
    return cmap, colorscale


def sigmoid_weighted(x, a=1):
    """Sigmoid function with a weight."""
    return 2 * (1 / (1 + np.exp(-a * x)) - 1)


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
    print("Array: ", array)
    # Normalize the array
    normalized_array = norm(array)
    print("Norm: ", normalized_array)
    # Get the colors for the normalized array
    # func_array = sigmoid_weighted(normalized_array, a=10000)
    func_array = normalized_array
    color_table = cmap(func_array)

    for row in color_table:
        for cell_color in row:
            print("Color: ", cell_color)
            print("Hex: ", colors.rgb2hex(cell_color))

    # Convert the colors to hex
    hex_colors = [
        [colors.rgb2hex(cell_color) for cell_color in row] for row in color_table
    ]

    # Set all NaN values to white
    hex_colors = np.where(np.isnan(array), "#ffffff", hex_colors)

    # Transpose the hex_colors array using the zip function
    hex_colors = list(zip(*hex_colors, strict=True))
    return hex_colors


def get_hex_colour(normval, cmap="jet", invert=False, baw=False):
    """Return a hex colour from a matplotlib named cmap."""
    # Return white if the value is NaN
    if pd.isna(normval):
        return "#ffffff"
    if normval <= 0:
        return "#ffffff"
    # Convert the value to a color
    colormap = matplotlib.colormaps.get(cmap)
    rgb_color = colormap(normval)

    hex_color = colors.rgb2hex(rgb_color)
    if invert:
        hex_color = invert_color(hex_color, baw=baw)
    return hex_color


def invert_color(hex_color, hsv=False, baw=False):
    """Invert a color from its hex code."""
    # Remove the '#' character from the hex code
    if hex_color[0] == "#":
        hex_color = hex_color[1:]
    else:
        raise ValueError("Invalid hex color code")

    # Convert 3-digit hex color to 6-digit hex color
    if len(hex_color) == 3:
        hex_color = "".join([char * 2 for char in hex_color])

    if len(hex_color) != 6:
        raise ValueError("Invalid hex color code")

    # Convert the hex color to RGB
    r = int(hex_color[:2], 16)
    g = int(hex_color[2:4], 16)
    b = int(hex_color[4:], 16)

    if hsv:
        # Convert the RGB to HSV
        r, g, b = r / 255.0, g / 255.0, b / 255.0
        h, s, v = colors.rgb_to_hsv((r, g, b))
        h = (h + 0.5) % 1

        # Invert the hsv components
        i_h = 1 - h
        i_s = 1 - s
        i_v = 1 - v
        print(f"{h=}, {s=}, {v=}")
        print(f"{i_h=}, {i_s=}, {i_v=}")

        i_r, i_g, i_b = colors.hsv_to_rgb((i_h, i_s, i_v))
        print(f"{i_r=}, {i_g=}, {i_b=}")

        i_r_hex = hex(int(i_r * 255))[2:].zfill(2)
        i_g_hex = hex(int(i_g * 255))[2:].zfill(2)
        i_b_hex = hex(int(i_b * 255))[2:].zfill(2)
        print(f"before: #{hex_color}")
        print(f"after: #{i_r_hex}{i_g_hex}{i_b_hex}")

        return f"#{i_r_hex}{i_g_hex}{i_b_hex}"

    # if black and white color scheme is selected (baw)
    if baw:
        # // https://stackoverflow.com/a/3943023/112731
        return (r * 0.299 + g * 0.587 + b * 0.114) > 186 and "#000000" or "#ffffff"

    # convert the RGB to inverted RGB, then to hex, padded with zeros
    i_r = hex(255 - r)[2:].zfill(2)
    i_g = hex(255 - g)[2:].zfill(2)
    i_b = hex(255 - b)[2:].zfill(2)
    print(f"before: #{hex_color}")
    print(f"after: #{i_r}{i_g}{i_b}")

    return f"#{i_r}{i_g}{i_b}"


def timedelta_to_human_readable(time_delta):
    """Convert a timedelta object to a nice human readable string.

    Example:
    --------
    9 days 17:20:00 -> "9.5d"
    0 days 06:30:00 -> "6.5h"
    0 days 00:10:00 -> "<1h"
    """
    if pd.isna(time_delta):
        return "—"
    days = time_delta.days
    hours = time_delta.seconds // 3600
    minutes = (time_delta.seconds % 3600) // 60
    if days > 10:
        return f"{days}d"
    elif days > 0:
        return f"{days + hours / 24:.1f}d"
    elif hours > 0:
        return f"{hours + minutes / 60:.1f}h"
    else:
        return "<1h"


def timedelta_to_total_hours(time_delta):
    """Convert a timedelta object to a string showing total decimal hours.

    Example:
    --------
    9 days 17:20:00 -> "233.3h"
    0 days 06:30:00 -> "6.5h"
    0 days 00:10:00 -> "0.2h"
    """
    if pd.isna(time_delta):
        return "—"
    total_hours = time_delta.total_seconds() / 3600
    return f"{total_hours:.3g}h"


if __name__ == "__main__":
    # Read the missing value csv file into pandas DataFrame
    # Columns of the dataframe are "Index, SiteName, [Measurement 1], [Measurement 2], ..."

    # total hours in one month
    total_hours_range = 1000

    missing_values = pd.read_csv("output_dump/output.csv")

    # Drop all rows that have NaN values in all columns except the first two columns
    missing_values = missing_values.dropna(
        axis=0, subset=missing_values.columns[1:], how="all"
    )

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

    # Convert all timedelta objects to total hours
    missing_values.loc[
        :,
        (missing_values.columns != "Index") & (missing_values.columns != "Sites"),
    ] = missing_values.loc[
        :,
        (missing_values.columns != "Index") & (missing_values.columns != "Sites"),
    ].map(
        lambda x: x.total_seconds() / 3600
    )

    bad_amount = 744

    normfunc = colors.Normalize(vmin=0, vmax=bad_amount)

    def style_cell_colour(val):
        """Return a pandas cell_color spec."""
        return f"background-color: {get_hex_colour(normfunc(val), cmap='autumn_r')}"

    def style_font_colour(val):
        """Return a pandas font_color spec."""
        return f"color: {invert_color(get_hex_colour(normfunc(val), cmap='autumn_r'), hsv=True)}"

    # Style the cell background color of the dataframe
    styled_df = missing_values.style.map(
        style_cell_colour, subset=missing_values.columns[1:]
    )

    # Style the font color of the dataframe
    styled_df = styled_df.applymap(style_font_colour, subset=missing_values.columns[1:])

    styled_df = styled_df.format(
        {
            col: lambda x: f"{x:.2f}h" if not pd.isna(x) else "—"
            for col in missing_values.columns[1:]
        }
    )

    # Remove the index column
    styled_df = styled_df.set_properties(**{"text-align": "left"}).hide()

    # Apply a monospace font both cells and headers
    styled_df.set_table_styles(
        [
            # Left align all the headers
            {"selector": "thead", "props": [("text-align", "left")]},
            # Set the cell fonts to mono space
            {"selector": "td", "props": [("font-family", "monospace")]},
            # Set the header fonts to mono space
            {"selector": "th", "props": [("font-family", "monospace")]},
            # Add a thin grey border around the cells
            {
                "selector": "table, td, th",
                "props": [
                    ("border", "1px solid #d3d3d3"),
                ],
            },
        ]
    )
    # Collapse the cell borders into single lines
    styled_df.set_properties(**{"border-collapse": "collapse"})

    html_report = styled_df.to_html(
        escape=False,
        classes="table table-striped table-bordered table-hover table-sm border-collapse",
        table_id="missing-values-table",
        justify="left",
    )

    # Output the html report to a file
    with open("output_dump/output.html", "w") as output_file:
        output_file.write(html_report)
