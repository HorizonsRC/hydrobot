"""Script to run through a processing task for rainfall."""

import pandas as pd

import hydrobot.config.horizons_source as source
import hydrobot.measurement_specific_functions.rainfall as rf
from hydrobot.filters import trim_series
from hydrobot.htmlmerger import HtmlMerger
from hydrobot.rf_processor import RFProcessor

#######################################################################################
# Reading configuration from config.yaml
#######################################################################################
data, ann = RFProcessor.from_config_yaml("rain_config.yaml")

#######################################################################################
# Importing external check data
#######################################################################################
data.check_data = source.rainfall_check_data(data.from_date, data.to_date, data.site)
# Put in zeroes at checks where there is no scada event
data.standard_data = rf.add_zeroes_at_checks(data.standard_data, data.check_data)
rainfall_inspections = source.rainfall_inspections(
    data.from_date, data.to_date, data.site
)

#######################################################################################
# Common auto-processing steps
#######################################################################################

# Clipping all data outside of low_clip and high_clip
data.clip()
# Remove manual tips
rainfall_inspections["primary_manual_tips"] = (
    rainfall_inspections["primary_manual_tips"].fillna(0).astype(int)
)
data.filter_manual_tips(rainfall_inspections)

#######################################################################################
# INSERT MANUAL PROCESSING STEPS HERE
# Can also add Annalist logging
#######################################################################################
# Example annalist log
# ann.logger.info("Deleting SOE check point on 2023-10-19T11:55:00.")

#######################################################################################
# Assign quality codes
#######################################################################################
dipstick_points = pd.Series(
    data=12,
    index=rainfall_inspections[rainfall_inspections["flask"].isna()]["arrival_time"],
)

data.quality_encoder(manual_additional_points=dipstick_points, synthetic_checks=[])
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

with open("check_table.html", "w", encoding="utf-8") as file:
    data.check_data.to_html(file)
with open("quality_table.html", "w", encoding="utf-8") as file:
    data.quality_data.to_html(file)
with open("inspections_table.html", "w", encoding="utf-8") as file:
    rainfall_inspections.to_html(file)
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
        "calibration_table.html",
        "potential_processing_issues.html",
    ],
    encoding="utf-8",
    header=f"<h1>{data.site}</h1>\n<h2>From {data.from_date} to {data.to_date}</h2>",
)

merger.merge()
