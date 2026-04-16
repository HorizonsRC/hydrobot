"""Script to run through a processing task for Groundwater."""

import numpy as np
import pandas as pd

import hydrobot.config.horizons_source as source
from hydrobot.filters import trim_series
from hydrobot.htmlmerger import HtmlMerger
from hydrobot.hydrobot_initialiser import initialise_hydrobot_from_yaml
from hydrobot.utils import series_rounder

checks_to_manually_ignore = []
data_sections_to_delete = []

#######################################################################################
# Reading configuration from config.yaml
#######################################################################################
data, ann = initialise_hydrobot_from_yaml("hydrobot_yaml_config_gw.yaml")

for bad_section in data_sections_to_delete:
    data.standard_data.loc[
        (data.standard_data.index > bad_section[0])
        & (data.standard_data.index < bad_section[1]),
        "Value",
    ] = np.nan

#######################################################################################
# Importing all check data
#######################################################################################
internal_sg = data.import_check(check_item_name="Internal S.G.")
data.check_data[data.check_data.Value == -1.0] = internal_sg[
    data.check_data.Value == -1.0
]

data.check_data = data.check_data[data.check_data.Value != -1.0]

comments_inspections = source.water_temperature_hydro_inspections(
    data.from_date, data.to_date, data.site
)
comments_ncr = source.non_conformances(data.site)

if data.check_data.empty:
    data.report_processing_issue(
        code="UCK",
        comment="No check data found - QCing as 200",
        series_type="Check",
        message_type="warning",
    )

# Any manual removals
for false_check in series_rounder(
    pd.Series(index=pd.DatetimeIndex(checks_to_manually_ignore)), "1min"
).index:
    data.check_data = data.check_data.drop(pd.Timestamp(false_check))

#######################################################################################
# Common auto-processing steps
#######################################################################################
data.pad_data_with_nan_to_set_freq()
data.clip()
# data.remove_flatlined_values()
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
data.quality_encoder()
data.standard_data["Value"] = trim_series(
    data.standard_data["Value"],
    data.check_data["Value"],
)

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
    file.write("<h3>Standard data</h3>")
    data.standard_data.to_html(file)
with open("check_table.html", "w", encoding="utf-8") as file:
    file.write("<h3>Check data</h3>")
    data.check_data.to_html(file)
with open("quality_table.html", "w", encoding="utf-8") as file:
    file.write("<h3>Quality data</h3>")
    data.quality_data.to_html(file)
with open("inspections_table.html", "w", encoding="utf-8") as file:
    file.write("<h3>Inspections</h3>")
    comments_inspections.to_html(file)
with open("ncr_table.html", "w", encoding="utf-8") as file:
    file.write("<h3>Non-conformances</h3>")
    comments_ncr.to_html(file)
with open("calibration_table.html", "w", encoding="utf-8") as file:
    file.write("<h3>Calibrations</h3>")
    source.calibrations(
        data.site, measurement_name=data.standard_measurement_name
    ).to_html(file)
with open("potential_processing_issues.html", "w", encoding="utf-8") as file:
    file.write("<h3>Hydrobot potential issues</h3>")
    data.processing_issues.to_html(file)

merger = HtmlMerger(
    [
        "pyplot.html",
        "potential_processing_issues.html",
        "check_table.html",
        "quality_table.html",
        "inspections_table.html",
        "ncr_table.html",
        "calibration_table.html",
    ],
    encoding="utf-8",
    header=f"<h1>{data.site}</h1>\n<h2>{data.standard_measurement_name}</h2>\n<h2>From {data.from_date} to {data.to_date}</h2>",
)

merger.merge()
