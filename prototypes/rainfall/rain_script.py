r"""Script to run through a processing task with the processor class.

Run command:

cd .\prototypes\rainfall
streamlit run .\rain_script.py

"""

import importlib.resources as pkg_resources
import platform

import pandas as pd
import sqlalchemy as db
from sqlalchemy.engine import URL

from hydrobot import utils
from hydrobot.filters import trim_series
from hydrobot.htmlmerger import HtmlMerger
from hydrobot.rf_processor import RFProcessor

#######################################################################################
# Reading configuration from config.yaml
#######################################################################################
data, ann = RFProcessor.from_config_yaml("rain_config.yaml")

#######################################################################################
# Importing all check data that is not obtainable from Hilltop
# (So far Hydrobot only speaks to Hilltop)
#######################################################################################
check_col = "Value"
logger_col = "Logger"

if platform.system() == "Windows":
    hostname = "SQL3.horizons.govt.nz"
elif platform.system() == "Linux":
    # Nic's WSL support (with apologies). THIS IS NOT STABLE.
    hostname = "PNT-DB30.horizons.govt.nz"
else:
    raise OSError("What is this, a mac? Get up on out of here, capitalist pig.")

s123_connection_url = URL.create(
    "mssql+pyodbc",
    host=hostname,
    database="survey123",
    query={"driver": "ODBC Driver 17 for SQL Server"},
)
s123_engine = db.create_engine(s123_connection_url)

inspection_query = """SELECT Hydro_Inspection.arrival_time,
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
rainfall_checks = pd.read_sql(
    inspection_query,
    s123_engine,
    params=(
        pd.Timestamp(data.from_date) - pd.Timedelta("3min"),
        pd.Timestamp(data.to_date) + pd.Timedelta("3min"),
        data.site,
    ),
)
# columns are:
# 'arrival_time', 'weather', 'notes', 'departure_time', 'creator',
# 'dipstick', 'check', 'flask', 'gauge_emptied', 'primary_total', 'start_time',
# 'end_time', 'primary_manual_tips', 'backup_manual_tips', 'pass'

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

data.check_data = utils.series_rounder(check_data)

all_checks = rainfall_checks.rename(
    columns={"primary_total": "Logger", "check": "Value"}
)
all_checks = all_checks.set_index("arrival_time")
all_checks["Source"] = "INS"
all_checks.index = pd.to_datetime(all_checks.index)
all_checks.loc[pd.Timestamp(data.from_date), "Value"] = 0
all_checks.loc[pd.Timestamp(data.from_date), "Logger"] = 0
all_checks["Value"] = all_checks["Value"].cumsum()
all_checks["Logger"] = all_checks["Logger"].cumsum()

#######################################################################################
# Getting the calibration data from the Assets database
#######################################################################################

ht_connection_url = URL.create(
    "mssql+pyodbc",
    host=hostname,
    database="hilltop",
    query={"driver": "ODBC Driver 17 for SQL Server"},
)
ht_engine = db.create_engine(ht_connection_url)

calibration_query = db.text(
    pkg_resources.files("hydrobot.config").joinpath("calibration_query.sql").read_text()
)

calibration_df = pd.read_sql(calibration_query, ht_engine, params={"site": data.site})

#######################################################################################
# Common auto-processing steps
#######################################################################################

# Clipping all data outside of low_clip and high_clip
data.clip()
# Remove manual tips
rainfall_checks["primary_manual_tips"] = (
    rainfall_checks["primary_manual_tips"].fillna(0).astype(int)
)
data.filter_manual_tips(rainfall_checks)

#######################################################################################
# INSERT MANUAL PROCESSING STEPS HERE
# Can also add Annalist logging!
#######################################################################################
# Example annalist log
# ann.logger.info("Deleting SOE check point on 2023-10-19T11:55:00.")

#######################################################################################
# Assign quality codes
#######################################################################################
dipstick_checks = pd.Series(
    data=12, index=rainfall_checks[rainfall_checks["flask"].isna()]["arrival_time"]
)

data.quality_encoder(
    manual_additional_points=dipstick_checks, synthetic_checks=["2024-03-06 09:32"]
)
data.standard_data["Value"] = trim_series(
    data.standard_data["Value"],
    data.check_data["Value"],
)

#######################################################################################
# Export all data to XML file
#######################################################################################

# Put in zeroes at checks where there is no scada event
empty_check_values = data.check_data[["Raw", "Value", "Changes"]].copy()
empty_check_values["Value"] = 0
empty_check_values["Raw"] = 0.0
empty_check_values["Changes"] = "RFZ"

# exclude values which are already in scada
empty_check_values = empty_check_values.loc[
    ~empty_check_values.index.isin(data.standard_data.index)
]
data.standard_data = pd.concat([data.standard_data, empty_check_values]).sort_index()

data.data_exporter()
# data.data_exporter("hilltop_csv", ftype="hilltop_csv")
# data.data_exporter("processed.csv", ftype="csv")

#######################################################################################
# Launch Hydrobot Processing Visualiser (HPV)
# Known issues:
# - No manual changes to check data points reflected in visualiser at this point
#######################################################################################

fig = data.plot_processing_overview_chart()
with open("pyplot.json", "w", encoding="utf-8") as file:
    file.write(str(fig.to_json()))
with open("pyplot.html", "w", encoding="utf-8") as file:
    file.write(str(fig.to_html()))

with open("check_table.html", "w", encoding="utf-8") as file:
    data.check_data.to_html(file)
with open("quality_table.html", "w", encoding="utf-8") as file:
    data.quality_data.to_html(file)
with open("calibration_table.html", "w", encoding="utf-8") as file:
    calibration_df.to_html(file)
with open("potential_processing_issues.html", "w", encoding="utf-8") as file:
    data.processing_issues.to_html(file)

merger = HtmlMerger(
    [
        "pyplot.html",
        "check_table.html",
        "quality_table.html",
        "calibration_table.html",
        "potential_processing_issues.html",
    ],
    encoding="utf-8",
    header=f"<h1>{data.site}</h1>\n<h2>From {data.from_date} to {data.to_date}</h2>",
)

merger.merge()
