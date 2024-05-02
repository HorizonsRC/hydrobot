r"""Script to run through a processing task with the processor class.

Run command:

cd .\prototypes\example_script\
streamlit run .\script.py

"""

import pandas as pd
import streamlit as st

from hydrobot.data_acquisition import (
    import_inspections,
    import_ncr,
    import_prov_wq,
)
from hydrobot.plotter import make_processing_dash
from hydrobot.processor import hydrobot_config_yaml_init
from hydrobot.utils import merge_all_comments

#######################################################################################
# Reading configuration from config.yaml
#######################################################################################

data, ann = hydrobot_config_yaml_init("config.yaml")

#######################################################################################
# Importing all check data that is not obtainable from Hilltop
# (So far Hydrobot only speaks to Hilltop)
#######################################################################################

inspections = import_inspections("WaterTemp_Inspections.csv")
prov_wq = import_prov_wq("WaterTemp_ProvWQ.csv")
ncrs = import_ncr("WaterTemp_non-conformance_reports.csv")

data.check_series = pd.concat(
    [
        data.check_series.rename("Temp Check"),
        inspections["Temp Check"]
        .drop(data.check_series.index, errors="ignore")
        .dropna(),
    ]
).sort_index()

data.check_series = data.check_series.loc[
    (data.check_series.index >= data.from_date)
    & (data.check_series.index <= data.to_date)
]

all_comments = merge_all_comments(data.raw_check_data, prov_wq, inspections, ncrs)


#######################################################################################
# Common auto-processing steps
#######################################################################################

# Clipping all data outside of low_clip and high_clip
data.clip()

# Remove obvious spikes using FBEWMA algorithm
data.remove_spikes()

# Inserting NaN values where clips and spikes created non-periodic gaps
data.insert_missing_nans()

# Closing all gaps smaller than gap_limit (i.e. removing nan values)
data.gap_closer()

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
st.set_page_config(page_title="Hydrobot0.5.1", layout="wide")
st.title(f"{data.site}")
st.header(f"{data.standard_measurement_name}")

fig = data.plot_qc_series(show=False)

fig_subplots = make_processing_dash(
    fig,
    data.site,
    data.raw_standard_series,
    data.standard_series,
    data.raw_check_data,
    prov_wq,
    inspections,
    ncrs,
)

st.plotly_chart(fig_subplots, use_container_width=True)

st.dataframe(all_comments, use_container_width=True)
