"""Script to run through a processing task for Water Temperature."""

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
data, ann = initialise_hydrobot_from_yaml("hydrobot_yaml_config_ph.yaml")

for bad_section in data_sections_to_delete:
    data.standard_data.loc[
        (data.standard_data.index > bad_section[0])
        & (data.standard_data.index < bad_section[1]),
        "Value",
    ] = np.nan

#######################################################################################
# Importing all check data
#######################################################################################
comments_inspections = source.water_temperature_hydro_inspections(
    data.from_date, data.to_date, data.site
)
comments_ncr = source.non_conformances(data.site)

depth_check = pd.DataFrame()
if data.depth:
    depth_check = data.interpolate_depth_profiles(
        data.depth / 1000.0, "Water Temperature (Depth Profile)"
    )
    depth_check = source.water_temp_check_formatter(depth_check, "DPF")
else:
    raise ValueError("depth required for this measurement")

check_data = [depth_check]

data.check_data = pd.concat([i for i in check_data if not i.empty])
data.check_data = data.check_data[
    ~data.check_data.index.duplicated(keep="first")
].sort_index()

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

# ann.logger.info(
#     "Upgrading chunk to 500 because only logger was replaced which shouldn't affect "
#     "the temperature sensor reading."
# )
# data.quality_series["2023-09-04T11:26:40"] = 500

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

with open("check_table.html", "w", encoding="utf-8") as file:
    data.check_data.to_html(file)
with open("quality_table.html", "w", encoding="utf-8") as file:
    data.quality_data.to_html(file)
with open("inspections_table.html", "w", encoding="utf-8") as file:
    comments_inspections.to_html(file)
with open("ncr_table.html", "w", encoding="utf-8") as file:
    comments_ncr.to_html(file)
with open("calibration_table.html", "w", encoding="utf-8") as file:
    source.calibrations(
        data.site, measurement_name=data.standard_measurement_name
    ).to_html(file)
with open("potential_processing_issues.html", "w", encoding="utf-8") as file:
    data.processing_issues.to_html(file)

merger = HtmlMerger(
    [
        "pyplot.html",
        "check_table.html",
        "quality_table.html",
        "inspections_table.html",
        "soe_table.html",
        "ncr_table.html",
        "calibration_table.html",
        "potential_processing_issues.html",
    ],
    encoding="utf-8",
    header=f"<h1>{data.site}</h1>\n<h2>From {data.from_date} to {data.to_date}</h2>",
)

merger.merge()
