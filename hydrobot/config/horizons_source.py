"""Location for Horizons specific configuration code."""

import importlib.resources as pkg_resources
import platform

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
    """Generate and return database engine."""
    s123_connection_url = URL.create(
        "mssql+pyodbc",
        host=sql_server_url(),
        database="survey123",
        query={"driver": "ODBC Driver 17 for SQL Server"},
    )
    return db.create_engine(s123_connection_url)


def rainfall_query():
    """Returns query used for Rainfall inspections."""
    query = """SELECT Hydro_Inspection.arrival_time,
            Hydro_Inspection.weather,
            Hydro_Inspection.notes,
            Hydro_Inspection.departure_time,
            Hydro_Inspection.creator,
            Rainfall_Inspection.dipstick,
            ISNULL(Rainfall_Inspection.flask, Rainfall_Inspection.dipstick) as 'check',
            Rainfall_Inspection.flask,
            Rainfall_Inspection.gauge_emptied,
            Rainfall_Inspection.primary_total,
            Manual_Tips.start_time,
            Manual_Tips.end_time,
            Manual_Tips.primary_manual_tips,
            Manual_Tips.backup_manual_tips,
            RainGauge_Validation.pass
        FROM [dbo].RainGauge_Validation
        RIGHT JOIN ([dbo].Manual_Tips
            RIGHT JOIN ([dbo].Rainfall_Inspection
                INNER JOIN [dbo].Hydro_Inspection
                ON Rainfall_Inspection.inspection_id = Hydro_Inspection.id)
            ON Manual_Tips.inspection_id = Hydro_Inspection.id)
        ON RainGauge_Validation.inspection_id = Hydro_Inspection.id
        WHERE Hydro_Inspection.arrival_time >= ?
            AND Hydro_Inspection.arrival_time < ?
            AND Hydro_Inspection.sitename = ?
            AND ISNULL(Rainfall_Inspection.flask, Rainfall_Inspection.dipstick) IS NOT NULL
        ORDER BY Hydro_Inspection.arrival_time ASC
        """
    return query


def rainfall_inspections(from_date, to_date, site):
    """Returns all info from rainfall inspection query."""
    rainfall_checks = pd.read_sql(
        rainfall_query(),
        survey123_db_engine(),
        params=(
            pd.Timestamp(from_date) - pd.Timedelta("3min"),
            pd.Timestamp(to_date) + pd.Timedelta("3min"),
            site,
        ),
    )
    return rainfall_checks


def rainfall_calibrations(site):
    """Return dataframe containing calibration info from assets."""
    ht_connection_url = URL.create(
        "mssql+pyodbc",
        host=sql_server_url(),
        database="hilltop",
        query={"driver": "ODBC Driver 17 for SQL Server"},
    )
    ht_engine = db.create_engine(ht_connection_url)

    calibration_query = db.text(
        pkg_resources.files("hydrobot.config")
        .joinpath("calibration_query.sql")
        .read_text()
    )

    calibration_df = pd.read_sql(calibration_query, ht_engine, params={"site": site})
    return calibration_df


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
