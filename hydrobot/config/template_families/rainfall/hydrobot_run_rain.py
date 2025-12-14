"""Script to run through a processing task for Rainfall."""
import numpy as np
import pandas as pd

import hydrobot.config.horizons_source as source
import hydrobot.measurement_specific_functions.rainfall as rf
import hydrobot.utils as utils
from hydrobot.filters import trim_series
from hydrobot.htmlmerger import HtmlMerger
from hydrobot.hydrobot_initialiser import initialise_hydrobot_from_yaml

#######################################################################################
# Manual interventions
#######################################################################################
synthetic_checks = []
checks_to_manually_ignore = []
backup_replacement_times = []

#######################################################################################
# Reading configuration from config.yaml
#######################################################################################
data, ann = initialise_hydrobot_from_yaml("hydrobot_yaml_config_rain.yaml")

#######################################################################################
# Importing external check data
#######################################################################################
data.check_data = source.rainfall_check_data(data.from_date, data.to_date, data.site)

# data.check_data.Value *= 1000
# data.check_data["Recorder Total"] = data.check_data.Value

# Any manual removals
for false_check in utils.series_rounder(
    pd.Series(index=pd.DatetimeIndex(checks_to_manually_ignore))
).index:
    data.check_data = data.check_data.drop(pd.Timestamp(false_check))
rainfall_inspections = source.rainfall_inspections(
    data.from_date, data.to_date, data.site
)

#######################################################################################
# Common auto-processing steps
#######################################################################################

#######################################################################################
# Rainfall specific operation
#######################################################################################
# Remove manual tips
rainfall_inspections["primary_manual_tips"] = (
    rainfall_inspections["primary_manual_tips"].fillna(0).astype(int)
)
data.filter_manual_tips(rainfall_inspections)

data.clip()

#######################################################################################
# INSERT MANUAL PROCESSING STEPS HERE
# Can also add Annalist logging
#######################################################################################
# Example annalist log
# ann.logger.info("Deleting SOE check point on 2023-10-19T11:55:00.")

# Changing to back up for this period
for time_period in backup_replacement_times:
    data.standard_data = utils.safe_concat(
        [
            data.standard_data[
                ~(
                    (data.standard_data.index >= time_period[0])
                    & (data.standard_data.index <= time_period[1])
                )
            ],
            data.import_standard(
                standard_hts_filename=data.standard_hts_filename,
                site=data.site,
                standard_measurement_name=data.backup_measurement_name,
                standard_data_source_name=data.backup_data_source_name,
                standard_item_info=data.standard_item_info,
                from_date=time_period[0],
                to_date=time_period[1],
            ),
        ]
    )
data.standard_data.sort_index()

# Put in zeroes at checks where there is no scada event
data.standard_data = rf.add_zeroes_at_checks(data.standard_data, data.check_data)

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

manual_additional_points = rf.manual_points_combiner(
    [dipstick_points, flask_points], checks_to_manually_ignore
)

if data.check_data.Value.isna().all():
    data_with_from_and_to_date_added = data.standard_data["Value"].copy()
    if data.from_date not in data_with_from_and_to_date_added:
        data_with_from_and_to_date_added[pd.Timestamp(data.from_date)] = 0
    if data.to_date not in data_with_from_and_to_date_added:
        data_with_from_and_to_date_added[pd.Timestamp(data.to_date)] = 0
    data_with_from_and_to_date_added = data_with_from_and_to_date_added.sort_index()
    data.ramped_standard = rf.rainfall_six_minute_repacker(
        data_with_from_and_to_date_added
    )
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
        backup_replacement_times=backup_replacement_times,
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
with open("standard_table.html", "w", encoding="utf-8") as file:
    file.write("<p>Standard Data</p>")
    data.standard_data.to_html(file)
with open("check_table.html", "w", encoding="utf-8") as file:
    file.write("<p>Check Data</p>")
    data.check_data.to_html(file)
with open("quality_table.html", "w", encoding="utf-8") as file:
    file.write("<p>Quality Data</p>")
    data.quality_data.to_html(file)
with open("inspections_table.html", "w", encoding="utf-8") as file:
    file.write("<p>Inspections</p>")
    rainfall_inspections.to_html(file)
with open("calibration_table.html", "w", encoding="utf-8") as file:
    file.write("<p>Calibrations</p>")
    utils.safe_concat(
        [
            source.calibrations(data.site, measurement_name="SCADA Rainfall"),
            source.calibrations(data.site, measurement_name="Rainfall"),
        ]
    ).to_html(file)
with open("inspections_table.html", "w", encoding="utf-8") as file:
    file.write("<p>All hydro inspections</p>")
    source.hydro_inspections(data.from_date, data.to_date, data.site).to_html(file)
with open("potential_processing_issues.html", "w", encoding="utf-8") as file:
    file.write("<p>Issues</p>")
    data.processing_issues.to_html(file)

merger = HtmlMerger(
    [
        "pyplot.html",
        "potential_processing_issues.html",
        "check_table.html",
        "quality_table.html",
        "inspections_table.html",
        "calibration_table.html",
    ],
    encoding="utf-8",
    header=f"<h1>{data.site}</h1>\n<h2>{data.standard_measurement_name}</h2>\n<h2>From {data.from_date} to {data.to_date}</h2>",
)

merger.merge()
