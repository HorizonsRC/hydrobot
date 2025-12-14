"""Location for Horizons specific configuration code."""

import importlib.resources as pkg_resources
import platform

import numpy as np
import pandas as pd
import sqlalchemy as db
import xmltodict
from sqlalchemy.engine import URL

from hydrobot import utils


def sql_server_url():
    """Return URL for SQL server host computer."""
    if platform.system() == "Windows":
        hostname = "SQL3.horizons.govt.nz"
    elif platform.system() == "Linux":
        # Nic's WSL support (with apologies). THIS IS NOT STABLE.
        hostname = "PNT-DB30.horizons.govt.nz"
    else:
        raise OSError("What is this, a mac? Get up on out of here, capitalist pig.")
    return hostname


def survey123_db_engine():
    """Generate and return survey123 database engine."""
    s123_connection_url = URL.create(
        "mssql+pyodbc",
        host=sql_server_url(),
        database="survey123",
        query={"driver": "ODBC Driver 17 for SQL Server"},
    )
    return db.create_engine(s123_connection_url)


def hilltop_db_engine():
    """Generate and return hilltop database engine."""
    ht_connection_url = URL.create(
        "mssql+pyodbc",
        host=sql_server_url(),
        database="hilltop",
        query={"driver": "ODBC Driver 17 for SQL Server"},
    )
    return db.create_engine(ht_connection_url)


def hydro_inspections(from_date, to_date, site):
    """Return hydro inspection info for site."""
    hydro_query = db.text(
        pkg_resources.files("hydrobot.config.horizons_sql")
        .joinpath("hydro_inspection.sql")
        .read_text()
    )

    inspections = pd.read_sql(
        hydro_query,
        survey123_db_engine(),
        params={
            "start_time": pd.Timestamp(from_date) - pd.Timedelta("3min"),
            "end_time": pd.Timestamp(to_date) + pd.Timedelta("3min"),
            "site": site,
        },
    )
    return inspections


def rainfall_inspections(from_date, to_date, site):
    """Returns all info from rainfall inspection query."""
    rainfall_query = db.text(
        pkg_resources.files("hydrobot.config.horizons_sql")
        .joinpath("rainfall_check.sql")
        .read_text()
    )

    rainfall_checks = pd.read_sql(
        rainfall_query,
        survey123_db_engine(),
        params={
            "start_time": pd.Timestamp(from_date) - pd.Timedelta("3min"),
            "end_time": pd.Timestamp(to_date) + pd.Timedelta("3min"),
            "site": site,
        },
    )

    # This rainfall site has multiple effective names
    if site == "Manawatu at Moutoa":
        rainfall_checks = (
            utils.safe_concat(
                [
                    rainfall_checks,
                    rainfall_inspections(
                        from_date, to_date, "Manawatu at Moutoa Gate Pier"
                    ),
                ]
            )
            .sort_values("arrival_time")
            .drop_duplicates()
        )
    return rainfall_checks


def water_temperature_hydro_inspections(from_date, to_date, site):
    """Returns all info from inspection query."""
    wt_query = db.text(
        pkg_resources.files("hydrobot.config.horizons_sql")
        .joinpath("water_temperature_check.sql")
        .read_text()
    )

    wt_checks = pd.read_sql(
        wt_query,
        survey123_db_engine(),
        params={
            "start_time": pd.Timestamp(from_date),
            "end_time": pd.Timestamp(to_date),
            "site": site,
        },
    )

    wt_checks["Index"] = wt_checks.loc[:, "inspection_time"].fillna(
        wt_checks.loc[:, "arrival_time"]
    )
    wt_checks = wt_checks.set_index("Index")
    wt_checks.index = pd.to_datetime(wt_checks.index)
    wt_checks.index.name = None
    return wt_checks


def dissolved_oxygen_hydro_inspections(from_date, to_date, site):
    """Returns all info from inspection query."""
    do_query = db.text(
        pkg_resources.files("hydrobot.config.horizons_sql")
        .joinpath("dissolved_oxygen_check.sql")
        .read_text()
    )

    do_checks = pd.read_sql(
        do_query,
        survey123_db_engine(),
        params={
            "start_time": pd.Timestamp(from_date),
            "end_time": pd.Timestamp(to_date),
            "site": site,
        },
    )

    do_checks["Index"] = (
        do_checks.loc[:, "inspection_time"]
        .astype("datetime64[ns]")
        .fillna(do_checks.loc[:, "arrival_time"])
    )
    do_checks = do_checks.set_index("Index")
    do_checks.index = pd.to_datetime(do_checks.index)
    do_checks.index.name = None
    return do_checks


def air_temperature_hydro_inspections(from_date, to_date, site):
    """Returns all info from inspection query."""
    at_query = db.text(
        pkg_resources.files("hydrobot.config.horizons_sql")
        .joinpath("air_temperature_check.sql")
        .read_text()
    )

    at_checks = pd.read_sql(
        at_query,
        survey123_db_engine(),
        params={
            "start_time": pd.Timestamp(from_date),
            "end_time": pd.Timestamp(to_date),
            "site": site,
        },
    )

    at_checks["Index"] = (
        at_checks.loc[:, "inspection_time"]
        .astype("datetime64[ns]")
        .fillna(at_checks.loc[:, "arrival_time"])
    )
    at_checks = at_checks.set_index("Index")
    at_checks.index = pd.to_datetime(at_checks.index)
    at_checks.index.name = None
    return at_checks


def atmospheric_pressure_inspections(from_date, to_date, site):
    """Get atmospheric pressure inspection data."""
    ap_query = db.text(
        pkg_resources.files("hydrobot.config.horizons_sql")
        .joinpath("atmospheric_pressure_check.sql")
        .read_text()
    )

    ap_checks = pd.read_sql(
        ap_query,
        survey123_db_engine(),
        params={
            "start_time": pd.Timestamp(from_date),
            "end_time": pd.Timestamp(to_date),
            "site": site,
        },
    )

    ap_checks["Index"] = ap_checks.loc[:, "inspection_time"].fillna(
        ap_checks.loc[:, "arrival_time"]
    )
    ap_checks = ap_checks.set_index("Index")
    ap_checks.index = pd.to_datetime(ap_checks.index)
    ap_checks.index.name = None
    return ap_checks


def calibrations(site, measurement_name):
    """Return dataframe containing calibration info from assets."""
    calibration_query = db.text(
        pkg_resources.files("hydrobot.config.horizons_sql")
        .joinpath("calibration_query.sql")
        .read_text()
    )

    calibration_df = pd.read_sql(
        calibration_query,
        hilltop_db_engine(),
        params={"site": site, "measurement_name": measurement_name},
    )
    if calibration_df.empty:
        calibration_query = db.text(
            pkg_resources.files("hydrobot.config.horizons_sql")
            .joinpath("sonde_calibration_query.sql")
            .read_text()
        )

        calibration_df = pd.read_sql(
            calibration_query,
            hilltop_db_engine(),
            params={"site": site},
        )
    return calibration_df


def non_conformances(site):
    """Return dataframe containing non-conformance info from assets."""
    non_conf_query = db.text(
        pkg_resources.files("hydrobot.config.horizons_sql")
        .joinpath("non_conformances.sql")
        .read_text()
    )

    non_conf_df = pd.read_sql(
        non_conf_query,
        survey123_db_engine(),
        params={"site": site},
    )
    return non_conf_df


def rainfall_check_data(from_date, to_date, site):
    """Filters inspection data to be in format for use as hydrobot check data."""
    rainfall_checks = rainfall_inspections(from_date, to_date, site)

    check_data = pd.DataFrame(
        rainfall_checks[["arrival_time", "check", "notes", "primary_total"]].copy()
    )

    check_data["Recorder Total"] = check_data.loc[:, "primary_total"] * 1000
    check_data["Recorder Time"] = check_data.loc[:, "arrival_time"]
    check_data = check_data.set_index("arrival_time")
    check_data.index = pd.to_datetime(check_data.index)
    check_data.index.name = None

    check_data = check_data.rename(columns={"check": "Raw", "notes": "Comment"})
    check_data["Value"] = check_data.loc[:, "Raw"]
    check_data["Time"] = pd.to_datetime(check_data["Recorder Time"], format="%H:%M:%S")
    check_data["Changes"] = ""
    check_data["Source"] = "INS"
    check_data["QC"] = True

    check_data = check_data[
        [
            "Time",
            "Raw",
            "Value",
            "Changes",
            "Recorder Time",
            "Recorder Total",
            "Comment",
            "Source",
            "QC",
        ]
    ]

    check_data = check_data[~check_data.duplicated()]

    if site == "Manawatu at Moutoa":
        check_data = (
            utils.safe_concat(
                [
                    check_data,
                    rainfall_check_data(
                        from_date, to_date, "Manawatu at Moutoa Gate Pier"
                    ),
                ]
            )
            .sort_index()
            .drop_duplicates()
        )

    return utils.series_rounder(check_data)


def water_temperature_hydro_check_data(from_date, to_date, site):
    """Filters water temperature hydro inspection data to be in format for use as hydrobot check data."""
    inspection_check_data = water_temperature_hydro_inspections(
        from_date, to_date, site
    )

    inspection_check_data["Time"] = inspection_check_data.loc[
        :, "inspection_time"
    ].fillna(inspection_check_data.loc[:, "arrival_time"])

    inspection_check_data = inspection_check_data.rename(
        columns={"handheld_temp": "Raw", "logger_temp": "Logger Temp"}
    )
    inspection_check_data["Value"] = inspection_check_data.loc[:, "Raw"]
    inspection_check_data["Comment"] = utils.combine_comments(
        inspection_check_data[["notes", "do_notes", "wl_notes"]].rename(
            columns={"notes": "HYDRO", "do_notes": "DO", "wl_notes": "WL"}
        )
    )
    inspection_check_data["Changes"] = ""
    inspection_check_data["Source"] = "INS"
    inspection_check_data["QC"] = True

    inspection_check_data = inspection_check_data[
        [
            "Time",
            "Raw",
            "Value",
            "Changes",
            "Logger Temp",
            "Comment",
            "Source",
            "QC",
        ]
    ]

    return inspection_check_data


def dissolved_oxygen_hydro_check_data(from_date, to_date, site):
    """Filters dissolved oxygen hydro inspection data to be in format for use as hydrobot check data."""
    inspection_check_data = dissolved_oxygen_hydro_inspections(from_date, to_date, site)

    inspection_check_data["Time"] = (
        inspection_check_data.loc[:, "inspection_time"]
        .astype("datetime64[ns]")
        .fillna(inspection_check_data.loc[:, "arrival_time"])
    )

    inspection_check_data = inspection_check_data.rename(
        columns={"handheld_percent": "Raw", "logger_percent": "Logger DO"}
    )
    inspection_check_data["Value"] = inspection_check_data.loc[:, "Raw"]
    inspection_check_data["Comment"] = utils.combine_comments(
        inspection_check_data[["notes", "do_notes", "wl_notes"]].rename(
            columns={"notes": "HYDRO", "do_notes": "DO", "wl_notes": "WL"}
        )
    )
    inspection_check_data["Changes"] = ""
    inspection_check_data["Source"] = "INS"
    inspection_check_data["QC"] = True

    inspection_check_data = inspection_check_data[
        [
            "Time",
            "Raw",
            "Value",
            "Changes",
            "Logger DO",
            "Comment",
            "Source",
            "QC",
        ]
    ]

    return inspection_check_data


def soe_check_data(processor, measurement):
    """Format water temperature SoE data for use as hydrobot check data."""
    soe_check = processor.get_measurement_dataframe(measurement, "check")
    soe_check.index.name = None
    soe_check.index = pd.DatetimeIndex(soe_check.index)
    soe_check["Time"] = soe_check.index
    soe_check["Value"] = soe_check["Value"].astype(np.float64)
    soe_check["Raw"] = soe_check["Value"]
    soe_check["Changes"] = ""
    soe_check["Comment"] = ""
    soe_check["Source"] = "SOE"
    soe_check["QC"] = True

    soe_check = soe_check[
        [
            "Time",
            "Raw",
            "Value",
            "Changes",
            "Comment",
            "Source",
            "QC",
        ]
    ]
    return soe_check


def atmospheric_pressure_hydro_check_data(from_date, to_date, site):
    """Filters atmospheric pressure hydro inspection data to be in format for use as hydrobot check data."""
    inspection_check_data = atmospheric_pressure_inspections(from_date, to_date, site)

    inspection_check_data["Time"] = inspection_check_data.loc[
        :, "inspection_time"
    ].fillna(inspection_check_data.loc[:, "arrival_time"])

    inspection_check_data = inspection_check_data.rename(
        columns={"handheld_baro": "Raw", "logger_baro": "Logger Baro"}
    )
    inspection_check_data["Value"] = inspection_check_data.loc[:, "Raw"]
    inspection_check_data["Comment"] = utils.combine_comments(
        inspection_check_data[["notes", "do_notes", "wl_notes"]].rename(
            columns={"notes": "WT", "do_notes": "DO", "wl_notes": "WL"}
        )
    )
    inspection_check_data["Changes"] = ""
    inspection_check_data["Source"] = "INS"
    inspection_check_data["QC"] = True

    inspection_check_data = inspection_check_data[
        [
            "Time",
            "Raw",
            "Value",
            "Changes",
            "Logger Baro",
            "Comment",
            "Source",
            "QC",
        ]
    ]

    return inspection_check_data


def find_three_letter_code(site):
    """Find three-letter code for a given site."""
    tlc_query = db.text(
        pkg_resources.files("hydrobot.config.horizons_sql")
        .joinpath("three_letter_site_code.sql")
        .read_text()
    )

    tlc_frame = pd.read_sql(
        tlc_query,
        hilltop_db_engine(),
        params={
            "site": site,
        },
    )
    if len(tlc_frame["AuxName2"]) > 0:
        return tlc_frame["AuxName2"].iloc[0]
    else:
        raise KeyError(f"Unable to find code for {site} in the database.")


def convert_check_series_to_check_frame(series: pd.Series, source: str):
    """
    Take a series and format it for check data.

    Parameters
    ----------
    series : pd.Series
        The series to be turned into a dataframe
    source : str
    """
    series.name = "Value"
    frame = pd.DataFrame(series)
    frame["Time"] = frame.index
    frame["Raw"] = frame["Value"]
    frame["Changes"] = ""
    frame["Comment"] = ""
    frame["Source"] = source
    frame["QC"] = True
    return frame


def site_info_lookup(site: str):
    """
    Find the hilltop site_info xml from the sql table and parses it as a dict.

    Parameters
    ----------
    site : str
        site to lookup

    Returns
    -------
    dict
        site_info xml as a dict
    """
    query = db.text(
        pkg_resources.files("hydrobot.config.horizons_sql")
        .joinpath("site_info_lookup.sql")
        .read_text()
    )

    result = pd.read_sql(
        query,
        hilltop_db_engine(),
        params={
            "site": site,
        },
    )

    xml_string = result.loc[0, "SiteInfo"]

    return xmltodict.parse(xml_string)["SiteInfo"]


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
    query = db.text(
        pkg_resources.files("hydrobot.config.horizons_sql")
        .joinpath("rainfall_site_inspection.sql")
        .read_text()
    )

    site_surveys = pd.read_sql(
        query,
        hilltop_db_engine(),
        params={
            "site": site,
        },
    )

    # Most recent filter
    """recent_survey = site_surveys[
        site_surveys["Arrival Time"] == site_surveys["Arrival Time"].max()
    ]"""

    return site_surveys
