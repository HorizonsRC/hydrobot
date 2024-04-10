"""Script to run through a processing task with the processor class."""

import pandas as pd
import streamlit as st
import yaml
from annalist.annalist import Annalist

from hydrobot.data_acquisition import (
    import_inspections,
    import_ncr,
    import_prov_wq,
)
from hydrobot.plotter import make_processing_dash
from hydrobot.processor import Processor
from hydrobot.utils import merge_all_comments

#######################################################################################
# Reading configuration from config.yaml
#######################################################################################

with open("config.yaml") as yaml_file:
    processing_parameters = yaml.safe_load(yaml_file)

#######################################################################################
# Setting up logging with Annalist
#######################################################################################

ann = Annalist()
ann.configure(
    logfile=processing_parameters["logfile"],
    analyst_name=processing_parameters["analyst_name"],
    stream_format_str=processing_parameters["format"]["stream"],
    file_format_str=processing_parameters["format"]["file"],
)

#######################################################################################
# Creating a Hydrobot Processor object which contains the data to be processed
#######################################################################################

data = Processor(
    processing_parameters["base_url"],
    processing_parameters["site"],
    processing_parameters["standard_hts_filename"],
    processing_parameters["standard_measurement_name"],
    processing_parameters["frequency"],
    processing_parameters["from_date"],
    processing_parameters["to_date"],
    processing_parameters["check_hts_filename"],
    processing_parameters["check_measurement_name"],
    processing_parameters["defaults"],
)

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
    (data.check_series.index >= processing_parameters["from_date"])
    & (data.check_series.index <= processing_parameters["to_date"])
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
# data.check_series = data.check_series.drop("2023-10-19T11:55:00")

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
st.title(f"{processing_parameters['site']}")
st.header(f"{processing_parameters['standard_measurement_name']}")

fig = data.plot_qc_series(show=False)

fig_subplots = make_processing_dash(
    fig,
    processing_parameters["site"],
    data.raw_standard_series,
    data.standard_series,
    data.raw_check_data,
    prov_wq,
    inspections,
    ncrs,
)

st.plotly_chart(fig_subplots, use_container_width=True)

st.dataframe(all_comments, use_container_width=True)

# fig_subplots.show()
# data.plot_qc_series(show=false)race(go.scatter())
# data.plot_gaps(show=False)
# data.plot_checks(show=False)
