r"""Script to run through a processing task with the processor class.

Run command:

cd .\prototypes\soil_moisture
streamlit run .\sm_script.py

"""

import pandas as pd
import streamlit as st

import hydrobot
from hydrobot.plotter import make_processing_dash
from hydrobot.processor import Processor

#######################################################################################
# Reading configuration from config.yaml
#######################################################################################

data, ann = Processor.from_config_yaml("sm_config.yaml")

st.set_page_config(
    page_title="Hydrobot" + hydrobot.__version__, layout="wide", page_icon="💦"
)
st.title(f"{data.site}")
st.header(f"{data.standard_measurement_name}")


#######################################################################################
# Common auto-processing steps
#######################################################################################


data.insert_missing_nans()

# Clipping all data outside of low_clip and high_clip
data.clip()

# Remove obvious spikes using FBEWMA algorithm
data.remove_spikes()

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
data.quality_data.loc[pd.Timestamp(data.from_date), "Value"] = 200
data.quality_data.loc[pd.Timestamp(data.to_date), "Value"] = 0


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
    pd.DataFrame(
        columns=[
            "Time",
            "Raw",
            "Value",
            "Changes",
            "Recorder Time",
            "Comment",
            "Source",
            "QC",
            "Logger",
        ]
    ).set_index("Time"),
)

st.plotly_chart(fig_subplots, use_container_width=True)

st.dataframe(data.standard_data, use_container_width=True)
st.dataframe(data.check_data, use_container_width=True)
st.dataframe(data.quality_data, use_container_width=True)
