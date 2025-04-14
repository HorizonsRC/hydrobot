"""Script to run through a processing task for Air Temperature."""

import pandas as pd

from hydrobot.htmlmerger import HtmlMerger
from hydrobot.hydrobot_initialiser import initialise_hydrobot_from_yaml

#######################################################################################
# Reading configuration from config.yaml and making processor object
#######################################################################################
data, ann = initialise_hydrobot_from_yaml("at_config.yaml")

#######################################################################################
# Common auto-processing steps
#######################################################################################
data.pad_data_with_nan_to_set_freq()
data.clip()
data.remove_spikes()

#######################################################################################
# INSERT MANUAL PROCESSING STEPS HERE
# Can also add Annalist logging
#######################################################################################
# Example annalist log
# ann.logger.info("Deleting SOE check point on 2023-10-19T11:55:00.")

#######################################################################################
# Assign quality codes
#######################################################################################
data.quality_data.loc[pd.Timestamp(data.from_date), "Value"] = 200
data.quality_data.loc[pd.Timestamp(data.to_date), "Value"] = 0

#######################################################################################
# Export all data to XML file
#######################################################################################
data.data_exporter()

#######################################################################################
# Write visualisation files
#######################################################################################
fig = data.plot_processing_overview_chart()

with open("pyplot.json", "w", encoding="utf-8") as file:
    file.write(str(fig.to_json()))
with open("pyplot.html", "w", encoding="utf-8") as file:
    file.write(str(fig.to_html()))

with open("standard_table.html", "w", encoding="utf-8") as file:
    data.standard_data.to_html(file)
with open("check_table.html", "w", encoding="utf-8") as file:
    data.check_data.to_html(file)
with open("quality_table.html", "w", encoding="utf-8") as file:
    data.quality_data.to_html(file)
with open("potential_processing_issues.html", "w", encoding="utf-8") as file:
    data.processing_issues.to_html(file)

merger = HtmlMerger(
    [
        "pyplot.html",
        "check_table.html",
        "quality_table.html",
        "potential_processing_issues.html",
    ],
    encoding="utf-8",
    header=f"<h1>{data.site}</h1>\n<h2>From {data.from_date} to {data.to_date}</h2>",
)

merger.merge()
