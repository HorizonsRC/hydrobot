"""Rainfall utils."""

import platform
import warnings

import numpy as np
import pandas as pd
import sqlalchemy as db
from sqlalchemy.engine import URL

import hydrobot.utils as utils

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
        survey_excel_sheet = r"\\ares\HydrologySoftware\Survey 123\RainfallSiteSurvey20220510_Pull\Rainfall_Site_Survey_20220510.xlsx"
        hostname = "SQL3.horizons.govt.nz"
    elif platform.system() == "Linux":
        # Support for Nic's personal WSL setup! Not generic linux support! Sorry!
        survey_excel_sheet = r"/mnt/ares_hydro_software/Survey 123/RainfallSiteSurvey20220510_Pull/RainfallSiteSurvey20220510.xlsx"
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
    site_surveys = site_survey_frame[
        (site_survey_frame["Site Name"] == site_index)
        | (site_survey_frame["New/un-official Site Name"] == site)
    ]

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
    pd.DataFrame
        Indexed by arrival time.
        Contains the following columns:

        matrix_sum : int
            Sum of points for NEMS matrix
        three_point_sum : int
            How many 3 points categories there are for NEMS matrix
        comment : string
            Comment from matrix
        output_dict: dict
            Keys are rows of NEMS matrix, values are the points contributed
    """
    all_site_surveys = rainfall_site_survey(site)
    with pd.option_context("future.no_silent_downcasting", True):
        all_site_surveys = all_site_surveys.ffill().bfill()

    survey_points_dict = {
        "matrix_sum": [],
        "three_point_sum": [],
        "comment": [],
        "output_dict": [],
    }
    survey_points_index = []
    for survey in all_site_surveys.index:
        site_surveys = all_site_surveys[
            all_site_surveys["Arrival Time"] <= all_site_surveys["Arrival Time"][survey]
        ]
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
            int(matrix_dict["Topography"])
            if not np.isnan(matrix_dict["Topography"])
            else 3
        )
        # Average annual windspeed
        output_dict["Average annual windspeed"] = (
            int(matrix_dict["Average annual windspeed"])
            if not np.isnan(matrix_dict["Average annual windspeed"])
            else 1  # 1 as region is almost all in the 3-6m/s category
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
        splash = (
            matrix_dict["Is there a Splash Guard for the Primary Reference Gauge?"] < 2
        )
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
            if output_dict[key] >= 3:
                three_point_sum += 1
        survey_points_dict["matrix_sum"].append(matrix_sum)
        survey_points_dict["three_point_sum"].append(three_point_sum)
        survey_points_dict["comment"].append(comment)
        survey_points_dict["output_dict"].append(output_dict)
        survey_points_index.append(
            most_recent_survey["Arrival Time"][most_recent_survey.index[0]]
        )

    return pd.DataFrame(data=survey_points_dict, index=survey_points_index)


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
    Sums a number of points with potentially different indices.

    e.g. series_a has index [a,c,f,g] with values [100,200,300,400]
    series_b has index [b,e,f] with values [10,20,30]
    the sum should be a series with index [a,b,c,e,f,g] with values [100,110,210,220,330,430]

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
    list_of_points_series: list[pd.Series], site_survey_frame: pd.DataFrame
):
    """
    Convert a points series to a quality code series.

    Parameters
    ----------
    list_of_points_series : List of pd.Series
        The series of points to be combined
    site_survey_frame : pd.DataFrame
        output of rainfall_nems_site_matrix()

    Returns
    -------
    pd.Series
        The series with quality codes
    """
    points_series = points_combiner(
        list_of_points_series + [site_survey_frame["matrix_sum"]]
    )

    # noinspection PyUnresolvedReferences
    greater_than_3_list = [(i >= 3).astype(int) for i in list_of_points_series]
    three_series = points_combiner(
        greater_than_3_list + [site_survey_frame["three_point_sum"]]
    )
    three_series = three_series.reindex(points_series.index, method="ffill")

    qc_series = pd.Series(0, index=points_series.index)

    # qc400
    qc_series += ((points_series >= 12) | (three_series >= 3)).astype(int) * 400

    # qc500
    qc_series += (
        (points_series >= 3) & (points_series < 12) & (three_series < 3)
    ).astype(int) * 500

    # qc600, needs to be >0 because qc0 is approx -1000 points
    qc_series += (
        (points_series >= 0) & (points_series < 3) & (three_series < 3)
    ).astype(int) * 600

    return qc_series


def manual_tip_filter(
    std_series: pd.Series,
    arrival_time: pd.Timestamp,
    departure_time: pd.Timestamp,
    manual_tips: int,
    weather: str = "",
    buffer_minutes: int = 10,
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
    buffer_minutes : int
        Increases search radius for tips that might be manual

    Returns
    -------
    pd.Series
        std_series with tips zeroed.
    dict | None
        Issue to report, if any
    """
    std_series = std_series.copy()
    if pd.isna(manual_tips):
        manual_tips = 0
    mode = std_series.astype(float).replace(0, np.nan).mode().item()

    if not isinstance(std_series.index, pd.DatetimeIndex):
        warnings.warn(
            "INPUT_WARNING: Index is not DatetimeIndex, index type will be changed",
            stacklevel=2,
        )
        std_series.index = pd.DatetimeIndex(std_series.index)

    offset = pd.Timedelta(minutes=buffer_minutes)
    inspection_data = std_series[
        (std_series.index > arrival_time - offset)
        & (std_series.index < departure_time + offset)
    ]

    if manual_tips == 0:
        # No manual tips to remove
        return std_series, None
    elif inspection_data.sum() <= ((manual_tips - 1.5) * mode):
        # Manual tips presumed to be in inspection mode, no further action
        return std_series, None
    else:
        # Count the actual amount of events, which may be grouped in a single second bucket
        events = (inspection_data.astype(np.float64).fillna(0.0).copy() / mode).astype(
            int
        )
        while not events[events > 1].empty:
            events = pd.concat(
                [events - 1, events[events > 1].apply(lambda x: 1)]
            ).sort_index()
        events = events.astype(np.float64)
        events[inspection_data > 0] = mode
        with pd.option_context("future.no_silent_downcasting", True):
            events[inspection_data.fillna(0).astype(int) <= 0] = 0

        if weather in ["Fine", "Overcast"] and np.abs(len(events) - manual_tips) <= 1:
            # Off by 1 is probably just a typo, delete it all
            std_series[inspection_data.index] = 0
            return std_series, None
        else:
            if not weather:
                weather = "NULL"
            if weather in ["Fine", "Overcast"]:
                comment = f"Weather {weather}, but more tips recorded than manual tips reported"
            else:
                comment = f"Inspection while weather is {weather}, verify manual tips removed were not real tips"
            issue = {
                "start_time": arrival_time,
                "end_time": departure_time,
                "code": "RMT",
                "comment": comment,
                "series_type": "standard,check",
                "message_type": "warning",
            }

            differences = (
                events.index[manual_tips - 1 :] - events.index[: -manual_tips + 1]
            )
            # Pandas do be pandering
            # All this does is find the first element of the shortest period
            first_manual_tip_index = pd.DataFrame(differences).idxmin().iloc[0]

            # Sufficiently intense
            events[first_manual_tip_index : first_manual_tip_index + manual_tips] = 0
            events = events.groupby(level=0).sum()

            std_series[inspection_data.index] = events

            return std_series, issue


def calculate_common_offset(
    standard_series: pd.Series,
    check_series: pd.Series,
    quality_series: pd.Series,
    threshold: int = 0,
) -> float:
    """
    Calculate common offset.

    Parameters
    ----------
    standard_series : pd.Series
        Standard series
    check_series : pd.Series
        Check series
    quality_series : pd.Series
        Quality series
    threshold : int
        Quality required to consider the value in the common offset

    Returns
    -------
    numeric
        The common offset
    """
    scada_difference = calculate_scada_difference(
        rainfall_six_minute_repacker(standard_series),
        check_series,
    )
    check_quality = quality_series.reindex(scada_difference.index, method="bfill")
    usable_checks = scada_difference[
        (check_quality >= threshold) & (np.abs(scada_difference - 1) < 0.2)
    ]
    return usable_checks.mean()


def add_zeroes_at_checks(standard_data: pd.DataFrame, check_data: pd.DataFrame):
    """
    Add zeroes in standard data where checks are, if there is no data there.

    Parameters
    ----------
    standard_data : pd.DataFrame
        Standard data that is potentially missing times
    check_data : pd.DataFrame
        Check data to potentially add zero values at set times.

    Returns
    -------
    pd.DataFrame
        The standard data with zeroes added

    """
    empty_check_values = check_data[["Raw", "Value", "Changes"]].copy()
    empty_check_values["Value"] = 0
    empty_check_values["Raw"] = 0.0
    empty_check_values["Changes"] = "RFZ"

    # exclude values which are already in scada
    empty_check_values = empty_check_values.loc[
        ~empty_check_values.index.isin(standard_data.index)
    ]
    standard_data = utils.safe_concat([standard_data, empty_check_values]).sort_index()
    return standard_data


def add_empty_rainfall_to_std(std_series: pd.Series, check_series: pd.Series):
    """
    Add zeroes to the std_series where checks happen (if no SCADA event then).

    Parameters
    ----------
    std_series : pd.Series
        The series which might be missing the zeroes
    check_series : pd.Series
        Where to add the zeroes if they don't exist

    Returns
    -------
    pd.Series
        std_series with zeroes added

    """
    # Prevent side effects
    std_series = std_series.copy()
    check_series = check_series.copy()

    # Find places for new zeroes
    additional_index_values = check_series.index.difference(std_series.index)
    additional_series = pd.Series(0, additional_index_values)

    if not additional_series.empty:
        std_series = pd.concat([std_series, additional_series])
    std_series = std_series.sort_index()

    return std_series


def calculate_scada_difference(std_series, check_series):
    """
    Calculate multiplicative difference between scada totals and check data.

    Parameters
    ----------
    std_series : pd.Series
        The series to be ramped. Values are required at each check value (can be zero)
    check_series : pd.Series
        The data to ramp it to

    Returns
    -------
    pd.Series
        Deviation of check series from scada totals
    """
    # Avoid side effects
    std_series = std_series.copy()
    check_series = check_series.copy()

    # How much rainfall has occurred according to scada
    incremental_series = std_series.cumsum()

    # Filter to when checks occur
    try:
        recorded_totals = incremental_series[check_series.index]
    except KeyError as e:
        raise KeyError("Check data times not found in the standard series") from e

    # Multiplier of difference between check and scada
    scada_difference = check_series / recorded_totals.diff().astype(np.float64).replace(
        0, np.nan
    )
    return scada_difference


def check_data_ramp_and_quality(std_series: pd.Series, check_series: pd.Series):
    """
    Ramps standard data to fit the check data.

    Parameters
    ----------
    std_series : pd.Series
        The series to be ramped. Values are required at each check value (can be zero)
    check_series : pd.Series
        The data to ramp it to

    Returns
    -------
    (pd.Series, pd.Series)
        First element is std_series but ramped
        Second element is quality_series
    """
    # Avoid side effects
    std_series = std_series.copy()
    check_series = check_series.copy()

    scada_difference = calculate_scada_difference(std_series, check_series)

    # Fill out to all scada events
    multiplier = scada_difference.reindex(std_series.index, method="bfill")
    # Multiply to find std_data
    std_series = std_series * multiplier.astype(np.float64).fillna(0.0)

    # Boolean whether it meets qc 600 standard
    points0 = (scada_difference >= 0.9) & (scada_difference <= 1.1)
    points3 = ((scada_difference >= 0.8) & (scada_difference <= 1.2)) & ~(
        (scada_difference >= 0.9) & (scada_difference <= 1.1)
    )
    points12 = ~((scada_difference >= 0.8) & (scada_difference <= 1.2))

    # Either QC 600 or 400
    # noinspection PyUnresolvedReferences
    quality_code = (
        points0.astype(np.float64) * 0
        + points3.astype(np.float64) * 3
        + points12.astype(np.float64) * 12
    )
    # Shift quality codes for hilltop convention
    quality_code = quality_code.shift(periods=-1)
    quality_code = quality_code.fillna(-1000).astype(np.int64)

    return std_series, quality_code


def rainfall_six_minute_repacker(series: pd.Series):
    """
    Repacks SCADA rainfall (rainfall bucket events) as 6 minute totals.

    Parameters
    ----------
    series : pd.Series
        SCADA rainfall series to be repacked as a 6 minute totals series
        expects a datetime index, will throw warning if it is not while it converts

    Returns
    -------
    pd.Series
        Repacked series with datetime index
    """
    series = series.copy()

    if not isinstance(series.index, pd.DatetimeIndex):
        warnings.warn(
            "INPUT_WARNING: Index is not DatetimeIndex, index type will be changed",
            stacklevel=2,
        )
        series.index = pd.DatetimeIndex(series.index)

    scada_index = series.index
    floor_index = scada_index.floor("6min")
    ceil_index = scada_index.ceil("6min")

    diff_filter = scada_index.diff() < pd.Timedelta(minutes=6)
    dup_filter = floor_index.duplicated()

    # Case 1, diff > 6

    time_delta_index_case1 = (scada_index - floor_index) / pd.Timedelta(minutes=6)

    floor_series = series[~diff_filter] * (1 - time_delta_index_case1[~diff_filter])
    floor_series.index = floor_index[~diff_filter]

    ceil_series = series[~diff_filter] * time_delta_index_case1[~diff_filter]
    ceil_series.index = ceil_index[~diff_filter]

    case1 = pd.concat([ceil_series, floor_series]).astype(float).round(3)
    case1 = case1.groupby(case1.index).sum()

    # Case 2, diff < 6 & last scada within timespan

    case2 = series[diff_filter & dup_filter]
    case2.index = ceil_index[diff_filter & dup_filter]
    case2 = case2.groupby(case2.index).sum()

    # Case 3, diff < 6 & last scada in other timespan

    time_delta_index_case3 = (scada_index - floor_index) / (scada_index.diff())

    floor_series = series[diff_filter & ~dup_filter] * (
        1 - time_delta_index_case3[diff_filter & ~dup_filter]
    )
    floor_series.index = floor_index[diff_filter & ~dup_filter]

    ceil_series = (
        series[diff_filter & ~dup_filter]
        * time_delta_index_case3[diff_filter & ~dup_filter]
    )
    ceil_series.index = ceil_index[diff_filter & ~dup_filter]

    case3 = pd.concat([ceil_series, floor_series]).astype(float).round(3)
    case3 = case3.groupby(case3.index).sum()

    # Putting it together

    rainfall_series = pd.concat([case1, case2, case3])
    rainfall_series = rainfall_series.groupby(rainfall_series.index).sum()

    # fill it up with zeroes
    rainfall_series = rainfall_series.asfreq(freq="6min", fill_value=0.0)

    return rainfall_series
