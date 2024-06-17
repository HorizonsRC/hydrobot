r"""Script to run through a processing task with the processor class.

Run command:

cd .\prototypes\rainfall
streamlit run .\rain_script.py

"""

import pandas as pd
import sqlalchemy as db
import streamlit as st

from hydrobot.filters import trim_series
from hydrobot.plotter import make_processing_dash
from hydrobot.rf_processor import RFProcessor

#######################################################################################
# Reading configuration from config.yaml
#######################################################################################

data, ann = RFProcessor.from_config_yaml("rain_config.yaml")

st.set_page_config(page_title="Hydrobot", layout="wide", page_icon="💦")
st.title(f"{data.site}")
st.header(f"{data.standard_measurement_name}")

#######################################################################################
# Importing all check data that is not obtainable from Hilltop
# (So far Hydrobot only speaks to Hilltop)
#######################################################################################

check_col = "Value"
logger_col = "Logger"

engine = db.create_engine(
    "mssql+pyodbc://SQL3/survey123?DRIVER=ODBC+Driver+17+for+SQL+Server"
)

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


check_data = pd.DataFrame(rainfall_checks["arrival_time"].copy())
check_data.index = pd.Index(check_data)
check_data["arrival_time"] = check_data.rename(columns={"arrival_time": "Time, "})

rainfall_checks = rainfall_checks.loc[
    (rainfall_checks.arrival_time >= data.from_date)
    & (rainfall_checks.arrival_time <= data.to_date)
]
"""      "Time",
        "Raw",
        "Value",
        "Changes",
        "Recorder Time",
        "Comment",
        "Source",
        "QC",
        """

data.check_data = rainfall_checks

data.check_data = data.check_data.loc[
    (data.check_data.index >= data.from_date) & (data.check_data.index <= data.to_date)
]

all_comments = rainfall_checks
all_checks = rainfall_checks

#######################################################################################
# Common auto-processing steps
#######################################################################################

data.insert_missing_nans()

# Clipping all data outside of low_clip and high_clip
data.clip()

# Remove obvious spikes using FBEWMA algorithm
data.remove_spikes()

#######################################################################################
# DO specific operation
#######################################################################################

data.correct_do()

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
data.data_exporter("processed.xml")
# data.data_exporter("hilltop_csv", ftype="hilltop_csv")
# data.data_exporter("processed.csv", ftype="csv")

#######################################################################################
# Launch Hydrobot Processing Visualiser (HPV)
# Known issues:
# - No manual changes to check data points reflected in visualiser at this point
#######################################################################################
fig = data.plot_qc_series(show=False)

fig_subplots = make_processing_dash(
    fig,
    data,
    all_checks,
)

st.plotly_chart(fig_subplots, use_container_width=True)

st.dataframe(all_comments, use_container_width=True)
# st.dataframe(data.standard_data, use_container_width=True)
st.dataframe(data.check_data, use_container_width=True)
st.dataframe(data.quality_data, use_container_width=True)
