"""Rainfall utils."""

import platform
import warnings

import numpy as np
import pandas as pd
import sqlalchemy as db
from sqlalchemy.engine import URL

# "optional" dependency needed: openpyxl
# pip install openpyxl


def rainfall_site_survey(site: str):
    """
    Gets most recent rainfall site survey for NEMs matrix.

    Parameters
    ----------
    site : str
        Name of site

    Returns
    -------
    pd.DataFrame
        The Dataframe with one entry, the most recent survey for the given site.
    """
    # Horizons sheet location
    if platform.system() == "Windows":
        survey_excel_sheet = (
            r"\\ares\HydrologySoftware\Survey "
            r"123\RainfallSiteSurvey20220510_Pull\RainfallSiteSurvey20220510.xlsx"
        )
        hostname = "SQL3.horizons.govt.nz"
    elif platform.system() == "Linux":
        # Support for Nic's personal WSL setup! Not generic linux support! Sorry!
        survey_excel_sheet = r"/mnt/ares_software/Survey 123/RainfallSiteSurvey20220510_Pull/RainfallSiteSurvey20220510.xlsx"
        hostname = "PNT-DB30.horizons.govt.nz"
    else:
        raise OSError("What is this, a mac? We don't do that here.")

    site_survey_frame = pd.ExcelFile(survey_excel_sheet).parse()

    # get site index from site name
    connection_url = URL.create(
        "mssql+pyodbc",
        host=hostname,
        database="survey123",
        query={"driver": "ODBC Driver 17 for SQL Server"},
    )
    # engine = db.create_engine(
    #     "mssql+pyodbc://SQL3.horizons.govt.nz/survey123?DRIVER=ODBC+Driver+17+for+SQL+Server"
    # )
    engine = db.create_engine(connection_url)
    query = """
            SELECT TOP (100000) [SiteID]
                ,[SiteName]
            FROM [survey123].[dbo].[Sites]
            WHERE SiteName = ?
            """
    site_lookup = pd.read_sql(query, engine, params=(site,))
    site_index = site_lookup.SiteID.iloc[0]

    # get inspections at site
    site_surveys = site_survey_frame[site_survey_frame["Site Name"] == site_index]

    # Most recent filter
    """recent_survey = site_surveys[
        site_surveys["Arrival Time"] == site_surveys["Arrival Time"].max()
    ]"""

    return site_surveys.sort_values(by=["Arrival Time"])


def rainfall_nems_site_matrix(site):
    """
    Finds the relevant site info from the spreadsheet and converts it into static points.

    Parameters
    ----------
    site : str
        The site to check for

    Returns
    -------
    int
        The static poitns from the site survey
    """
    site_surveys = rainfall_site_survey(site)
    most_recent_survey = site_surveys[
        site_surveys["Arrival Time"] == site_surveys["Arrival Time"].max()
    ]

    # Gets the usable index in cases where more recent surveys omit some info
    valid_indices = site_surveys.apply(pd.Series.last_valid_index).fillna(
        most_recent_survey.index[0]
    )

    # Turn those indices into usable info
    matrix_dict = {}
    for index in valid_indices.index:
        matrix_dict[index] = site_surveys[index][valid_indices[index]]

    # Fill out NEMS point values from matrix
    output_dict = {}

    # Topography
    output_dict["Topography"] = (
        int(matrix_dict["Topography"]) if not np.isnan(matrix_dict["Topography"]) else 3
    )
    # Average annual windspeed
    output_dict["Average annual windspeed"] = (
        int(matrix_dict["Average annual windspeed"])
        if not np.isnan(matrix_dict["Average annual windspeed"])
        else 3
    )
    # Obstructed Horizon
    output_dict["Obstructed Horizon"] = (
        int(matrix_dict["Obstructed Horizon"])
        if not np.isnan(matrix_dict["Obstructed Horizon"])
        else 3
    )
    # Distance between Primary Reference Gauge (Check Gauge) and the Intensity Gauge (mm)
    dist = matrix_dict[
        "Distance between Primary Reference Gauge (Check Gauge) and the Intensity Gauge (mm)"
    ]
    if 600 <= dist <= 2000:
        output_dict["Distance Between Gauges"] = 0
    else:
        output_dict["Distance Between Gauges"] = 3  # including nan
    # Orifice Height - Primary Reference Gauge
    splash = matrix_dict["Is there a Splash Guard for the Primary Reference Gauge?"] > 2
    height = matrix_dict[
        "Orifice height of the Primary Reference Gauge (Check Gauge) (mm)"
    ]
    if splash or (285 <= height <= 325):
        output_dict["Orifice Height - Primary Reference Gauge"] = 0
    else:
        output_dict["Orifice Height - Primary Reference Gauge"] = 3
    # Orifice Diameter - Primary Reference Gauge
    dist = matrix_dict[
        "Orifice diameter of the Primary Reference Gauge (Check Gauge)(mm)"
    ]
    if 125 <= dist <= 205:
        output_dict["Orifice Diameter"] = 0
    else:
        output_dict["Orifice Diameter"] = 3  # including nan
    # Orifice height - Intensity Gauge
    height = matrix_dict[
        "Orifice height of the Primary Reference Gauge (Check Gauge) (mm)"
    ]
    if splash or (285 <= height <= 600):
        output_dict["Orifice height - Intensity Gauge"] = 0
    elif height <= 1000:
        height_diff = np.abs(
            height
            - matrix_dict[
                "Orifice height of the Primary Reference Gauge (Check Gauge) (mm)"
            ]
        )
        if height_diff <= 50:
            output_dict["Orifice height - Intensity Gauge"] = 1
        else:
            output_dict["Orifice height - Intensity Gauge"] = 3
    else:
        output_dict["Orifice height - Intensity Gauge"] = 3
    # Orifice Diameter - Intensity  Gauge
    dist = matrix_dict["Orifice Diameter of the Intensity Gauge (mm)"]
    if 125 <= dist <= 205:
        output_dict["Orifice Diameter Intensity"] = 0
    else:
        output_dict["Orifice Diameter Intensity"] = 3  # including nan

    matrix_sum = 0
    three_point_sum = 0
    comment = matrix_dict["Potential effects on Data"]

    for key in output_dict:
        matrix_sum += output_dict[key]
        if output_dict[key] > 2:
            three_point_sum += 1

    return matrix_sum, three_point_sum, comment, output_dict


def rainfall_time_since_inspection_points(
    check_series: pd.Series,
):
    """
    Calculates points from the NEMS matrix for quality coding.

    Only applies a single cap quality code, see bulk_downgrade_out_of_validation for multiple steps.

    Parameters
    ----------
    check_series : pd.Series
        Check series to check for frequency of checks

    Returns
    -------
    pd.Series
        check_series index with points to add
    """
    # Stop side effects
    check_series = check_series.copy()
    # Error checking
    if check_series.empty:
        raise ValueError("Cannot have empty rainfall check series")
    if not isinstance(check_series.index, pd.core.indexes.datetimes.DatetimeIndex):
        warnings.warn(
            "INPUT_WARNING: Index is not DatetimeIndex, index type will be changed",
            stacklevel=2,
        )
        check_series = pd.DatetimeIndex(check_series.index)

    # Parameters
    cutoff_times = {
        18: 12,
        12: 3,
        3: 1,
    }

    def max_of_two_series(a, b):
        """Takes maximum value from two series with same index."""
        if not b.index.equals(a.index):
            raise ValueError("Series must have same index")
        return a[a >= b].reindex(a.index, fill_value=0) + b[a < b].reindex(
            b.index, fill_value=0
        )

    months_diff = []
    for time, next_time in zip(
        check_series.index[:-1], check_series.index[1:], strict=True
    ):
        months_gap = (next_time.year - time.year) * 12 + (next_time.month - time.month)
        if next_time.day <= time.day:
            # Not a full month yet, ignoring time stamp
            months_gap -= 1
        months_diff.append(months_gap)
    months_diff = pd.Series(months_diff, index=check_series.index[:-1])

    points_series = pd.Series(0, index=check_series.index[:-1])
    for months in cutoff_times:
        cutoff_series = (months_diff >= months).astype(int) * cutoff_times[months]
        points_series = max_of_two_series(points_series, cutoff_series)

    points_series = points_series.reindex(check_series.index, fill_value=-1000)
    return points_series


def points_combiner(list_of_points_series: list[pd.Series]):
    """
    Combines a number of points with potentially different indices.

    Parameters
    ----------
    list_of_points_series : List of pd.Series
        The series to be combined

    Returns
    -------
    pd.Series
        Combined series
    """
    # Filter empty series out
    list_of_points_series = [i.copy() for i in list_of_points_series if not i.empty]
    if not list_of_points_series:
        raise ValueError("At least one series must not be empty.")

    # Make combined index
    new_index = list_of_points_series[0].index
    for i in list_of_points_series[1:]:
        new_index = new_index.union(i.index)
    new_index = new_index.sort_values()

    # Add first values
    temp = list_of_points_series
    list_of_points_series = []
    for i in temp:
        if new_index[0] not in i:
            i[new_index[0]] = 0
            list_of_points_series.append(i.sort_index())
        else:
            list_of_points_series.append(i)

    # Put series to combined series index and combine values
    list_of_points_series = [
        i.reindex(new_index, method="ffill") for i in list_of_points_series
    ]
    points_series = sum(list_of_points_series)

    # Remove consecutive duplicates
    points_series = points_series.loc[points_series.shift() != points_series]

    return points_series


def points_to_qc(
    list_of_points_series: list[pd.Series],
    static_points: int,
    three_points_total: int,
):
    """
    Convert a points series to a quality code series.

    Parameters
    ----------
    list_of_points_series : List of pd.Series
        The series of points to be combined
    static_points : int
        How many points from the site survey
    three_points_total : int
        Number of values which hit the 3 point threshold

    Returns
    -------
    pd.Series
        The series with quality codes
    """
    points_series = points_combiner(list_of_points_series)

    greater_than_3_list = [i.astype(int) for i in list_of_points_series]
    three_series = points_combiner(greater_than_3_list) + three_points_total

    qc_series = pd.Series(0, index=points_series.index)

    # qc400
    qc_series += ((points_series >= 12) | (three_series >= 3)).astype(int) * 400

    # qc500
    qc_series += ((points_series >= 3) & (points_series < 12)).astype(int) * 500

    # qc600, needs to be >0 because qc0 is approx -1000 points
    qc_series += ((points_series >= 0) & (points_series < 3)).astype(int) * 600

    return qc_series


def manual_tip_filter(
    std_series: pd.Series,
    arrival_time: pd.Timestamp,
    departure_time: pd.Timestamp,
    manual_tips: int,
    weather: str = "",
):
    """
    Sets any manual tips to 0 for a single inspection.

    Parameters
    ----------
    std_series : pd.Series
        The rainfall data to have manual tips removed. Must be datetime indexable
    arrival_time : pd.Timestamp
        The start of the inspection
    departure_time : pd.Timestamp
        The end of the inspection
    manual_tips : int
        Number of manual tips
    weather : str
        Type of weather at inspection

    Returns
    -------
    pd.Series
        std_series with tips zeroed.
    dict | None
        Issue to report, if any
    """
    std_series = std_series.copy()
    threshold = pd.Timedelta("00:00:20")

    if not isinstance(std_series.index, pd.DatetimeIndex):
        warnings.warn(
            "INPUT_WARNING: Index is not DatetimeIndex, index type will be changed",
            stacklevel=2,
        )
        std_series.index = pd.DatetimeIndex(std_series.index)

    inspection_data = std_series[
        (std_series.index > arrival_time) & (std_series.index < departure_time)
    ]

    if len(inspection_data) < manual_tips:
        # Manual tips presumed to be in inspection mode, no further action
        return std_series, None
    elif manual_tips == 0:
        # No manual tips to remove
        return std_series, None
    else:
        if weather in ["Fine", "Overcast"]:
            if abs(manual_tips - len(inspection_data)) <= 1:
                # Off by 1 is probably just a typo, delete it all
                std_series[inspection_data.index] = 0

                return std_series, None
            else:
                issue = {
                    "start_time": arrival_time,
                    "end_time": departure_time,
                    "code": "RMT",
                    "comment": "Weather dry, but more tips recorded than manual tips reported",
                    "series_type": "Standard and Check",
                }
                differences = (
                    inspection_data.index[manual_tips - 1 :]
                    - inspection_data.index[: -manual_tips + 1]
                )
                # Pandas do be pandering
                # All this does is find the first element of the shortest period
                first_manual_tip_index = pd.DataFrame(differences).idxmin().iloc[0]

                if differences[first_manual_tip_index] < threshold:
                    # Sufficiently intense
                    inspection_data[
                        first_manual_tip_index : first_manual_tip_index + manual_tips
                    ] = 0
                    std_series[inspection_data.index] = inspection_data

                return std_series, issue
        else:
            if not weather:
                weather = "NULL"
            issue = {
                "start_time": arrival_time,
                "end_time": departure_time,
                "code": "RMT",
                "comment": f"Inspection while weather is {weather}, verify manual tips removed were not real tips",
                "series_type": "Standard and Check",
            }

            differences = (
                inspection_data.index[manual_tips - 1 :]
                - inspection_data.index[: -manual_tips + 1]
            )
            # Pandas do be pandering
            # All this does is find the first element of the shortest period
            first_manual_tip_index = pd.DataFrame(differences).idxmin().iloc[0]

            if differences[first_manual_tip_index] < threshold or manual_tips > 30:
                # Sufficiently intense or calibration
                inspection_data[
                    first_manual_tip_index : first_manual_tip_index + manual_tips
                ] = 0
                std_series[inspection_data.index] = inspection_data

            return std_series, issue