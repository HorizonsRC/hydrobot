r"""Script to run through a processing task with the processor class.

Run command:

cd .\prototypes\rainfall
streamlit run .\rain_script.py

"""

import platform

import pandas as pd
import pyodbc
import sqlalchemy as db
import streamlit as st
from rich.traceback import install
from sqlalchemy.engine import URL

import hydrobot
from hydrobot.filters import trim_series
from hydrobot.rf_processor import RFProcessor

install()

#######################################################################################
# Reading configuration from config.yaml
#######################################################################################

data, ann = RFProcessor.from_config_yaml("rain_config.yaml")

st.set_page_config(
    page_title="Hydrobot" + hydrobot.__version__, layout="wide", page_icon="💦"
)
st.title(f"{data.site}")
st.header(f"{data.standard_measurement_name}")

#######################################################################################
# Importing all check data that is not obtainable from Hilltop
# (So far Hydrobot only speaks to Hilltop)
#######################################################################################

check_col = "Value"
logger_col = "Logger"

st.write(pyodbc.drivers())

if platform.system() == "Windows":
    hostname = "SQL3.horizons.govt.nz"
elif platform.system() == "Linux":
    # Nic's WSL support (with apologies). THIS IS NOT STABLE.
    hostname = "PNT-DB30.horizons.govt.nz"
else:
    raise OSError("What is this, a mac? Get up on out of here, capitalist pig.")

connection_url = URL.create(
    "mssql+pyodbc",
    host=hostname,
    database="survey123",
    query={"driver": "ODBC Driver 17 for SQL Server"},
)
engine = db.create_engine(connection_url)

query = """SELECT TOP (10) Hydro_Inspection.arrival_time,
            Hydro_Inspection.weather,
            Hydro_Inspection.notes,
            Hydro_Inspection.departure_time,
            Hydro_Inspection.creator,
            Rainfall_Inspection.dipstick,
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
            AND Hydro_Inspection.arrival_time <= ?
            AND Hydro_Inspection.sitename = ?
        ORDER BY Hydro_Inspection.arrival_time ASC
        """
rainfall_checks = pd.read_sql(
    query, engine, params=(data.from_date, data.to_date, data.site)
)
# columns are:
# 'arrival_time', 'weather', 'notes', 'departure_time', 'creator',
# 'dipstick', 'flask', 'gauge_emptied', 'primary_total', 'start_time',
# 'end_time', 'primary_manual_tips', 'backup_manual_tips', 'pass'

rainfall_checks = rainfall_checks.loc[
    (rainfall_checks.arrival_time >= data.from_date)
    & (rainfall_checks.arrival_time <= data.to_date)
]

check_data = pd.DataFrame(rainfall_checks[["arrival_time", "flask", "notes"]].copy())

check_data["Recorder Time"] = check_data.loc[:, "arrival_time"]
check_data = check_data.set_index("arrival_time")
check_data.index = pd.to_datetime(check_data.index)
check_data.index.name = None

check_data = check_data.rename(columns={"flask": "Raw", "notes": "Comment"})
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
        "Comment",
        "Source",
        "QC",
    ]
]

data.check_data = check_data


all_checks = rainfall_checks.rename(
    columns={"primary_total": "Logger", "flask": "Value"}
)
all_checks = all_checks.set_index("arrival_time")
all_checks["Source"] = "INS"
all_checks.index = pd.to_datetime(all_checks.index)
all_checks.loc[pd.Timestamp(data.from_date), "Value"] = 0
all_checks.loc[pd.Timestamp(data.from_date), "Logger"] = 0
all_checks["Value"] = all_checks["Value"].cumsum()
all_checks["Logger"] = all_checks["Logger"].cumsum()

#######################################################################################
# Common auto-processing steps
#######################################################################################


# Clipping all data outside of low_clip and high_clip
data.clip()

# Remove manual tips
data.filter_manual_tips(rainfall_checks)

# Rainfall is cumulative
# data.standard_data.Value = data.standard_data.Value.cumsum()
# data.standard_data.Raw = data.standard_data.Raw.cumsum()

#######################################################################################
# INSERT MANUAL PROCESSING STEPS HERE
# Remember to add Annalist logging!
#######################################################################################

# Manually removing an erroneous check data point
# ann.logger.info(
#     "Deleting SOE check point on 2023-10-19T11:55:00. Looks like Darren recorded the "
#     "wrong temperature into Survey123 at this site."
# )
# data.check_series = pd.concat([data.check_series[:3], data.check_series[9:]])

#######################################################################################
# Assign quality codes
#######################################################################################
data.quality_encoder()
data.standard_data["Value"] = trim_series(
    data.standard_data["Value"],
    data.check_data["Value"],
)

# ann.logger.info(
#     "Upgrading chunk to 500 because only logger was replaced which shouldn't affect "
#     "the temperature sensor reading."
# )
# data.quality_series["2023-09-04T11:26:40"] = 500

#######################################################################################
# Export all data to XML file
#######################################################################################
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

st.dataframe(data.processing_issues, use_container_width=True)
st.dataframe(all_checks, use_container_width=True)
st.dataframe(data.check_data, use_container_width=True)
st.dataframe(data.quality_data, use_container_width=True)
st.dataframe(data.standard_data, use_container_width=True)
