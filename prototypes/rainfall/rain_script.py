"""Script to run through a processing task for Rainfall."""
import numpy as np
import pandas as pd

import hydrobot.config.horizons_source as source
import hydrobot.measurement_specific_functions.rainfall as rf
from hydrobot.filters import trim_series
from hydrobot.htmlmerger import HtmlMerger
from hydrobot.rf_processor import RFProcessor
from hydrobot.utils import rainfall_six_minute_repacker, series_rounder

#######################################################################################
# Manual interventions
#######################################################################################
synthetic_checks = []
checks_to_manually_ignore = []

#######################################################################################
# Reading configuration from config.yaml
#######################################################################################
data, ann = RFProcessor.from_config_yaml("rain_config.yaml", set_from_date=True)

#######################################################################################
# Importing external check data
#######################################################################################
data.check_data = source.rainfall_check_data(data.from_date, data.to_date, data.site)
# Any manual removals
for false_check in series_rounder(
    pd.Series(index=pd.DatetimeIndex(checks_to_manually_ignore))
).index:
    data.check_data = data.check_data.drop(pd.Timestamp(false_check))
# Put in zeroes at checks where there is no scada event
data.standard_data = rf.add_zeroes_at_checks(data.standard_data, data.check_data)
rainfall_inspections = source.rainfall_inspections(
    data.from_date, data.to_date, data.site
)

#######################################################################################
# Common auto-processing steps
#######################################################################################
data.clip()

#######################################################################################
# Rainfall specific operation
#######################################################################################
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

flask_points = pd.Series(
    data=0,
    index=rainfall_inspections[~rainfall_inspections["flask"].isna()]["arrival_time"],
)

manual_additional_points = [dipstick_points, flask_points]
manual_additional_points = [i for i in manual_additional_points if not i.empty]
if manual_additional_points:
    manual_additional_points = pd.concat(
        [i for i in manual_additional_points if not i.empty]
    )
    manual_additional_points = manual_additional_points.sort_index()
else:
    manual_additional_points = pd.Series({})

if data.check_data.empty:
    data.ramped_standard = rainfall_six_minute_repacker(data.standard_data["Value"])
    data.quality_data = pd.DataFrame(
        index=[data.ramped_standard.index[0], data.ramped_standard.index[-1]],
        data={
            "Time": [data.ramped_standard.index[0], data.ramped_standard.index[-1]],
            "Raw": [np.nan, np.nan],
            "Value": [200, 0],
            "Code": ["UCK", ""],
            "Details": ["", ""],
        },
    )
else:
    data.quality_encoder(
        manual_additional_points=manual_additional_points,
        synthetic_checks=synthetic_checks,
    )
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
