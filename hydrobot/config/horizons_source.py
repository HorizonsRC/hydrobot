"""Location for Horizons specific configuration code."""

import importlib.resources as pkg_resources
import platform

import numpy as np
import pandas as pd
import sqlalchemy as db
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
    return rainfall_checks


def water_temperature_hydro_inspections(from_date, to_date, site):
    """Returns all info from rainfall inspection query."""
    rainfall_query = db.text(
        pkg_resources.files("hydrobot.config.horizons_sql")
        .joinpath("water_temperature_check.sql")
        .read_text()
    )

    rainfall_checks = pd.read_sql(
        rainfall_query,
        survey123_db_engine(),
        params={
            "start_time": pd.Timestamp(from_date),
            "end_time": pd.Timestamp(to_date),
            "site": site,
        },
    )

    rainfall_checks["Index"] = rainfall_checks.loc[:, "inspection_time"].fillna(
        rainfall_checks.loc[:, "arrival_time"]
    )
    rainfall_checks = rainfall_checks.set_index("Index")
    rainfall_checks.index = pd.to_datetime(rainfall_checks.index)
    rainfall_checks.index.name = None
    return rainfall_checks


def atmospheric_pressure_inspections(from_date, to_date, site):
    """Get atmospheric pressure inspection data."""
    rainfall_query = db.text(
        pkg_resources.files("hydrobot.config.horizons_sql")
        .joinpath("atmospheric_pressure_check.sql")
        .read_text()
    )

    rainfall_checks = pd.read_sql(
        rainfall_query,
        survey123_db_engine(),
        params={
            "start_time": pd.Timestamp(from_date),
            "end_time": pd.Timestamp(to_date),
            "site": site,
        },
    )
    return rainfall_checks


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
            "Logger Temp",
            "Comment",
            "Source",
            "QC",
        ]
    ]

    return inspection_check_data


def water_temperature_soe_check_data(processor, measurement):
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


def atmospheric_pressure_field_wq_checks(from_date, to_date, site):
    """Get SoE data for atmospheric pressure."""
    pass
