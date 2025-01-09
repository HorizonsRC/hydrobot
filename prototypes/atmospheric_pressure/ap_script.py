"""Script to run through a processing task for Atmospheric Pressure."""

import pandas as pd

import hydrobot.config.horizons_source as source
from hydrobot.filters import trim_series
from hydrobot.htmlmerger import HtmlMerger
from hydrobot.processor import Processor
from hydrobot.utils import series_rounder

#######################################################################################
# Reading configuration from config.yaml
#######################################################################################
data, ann = Processor.from_config_yaml("ap_config.yaml")

#######################################################################################
# Importing all check data
#######################################################################################
comments_inspections = source.water_temperature_hydro_inspections(
    data.from_date, data.to_date, data.site
)
comments_soe = data.get_measurement_dataframe("Field Baro Pressure (HRC)", "check")
comments_soe.index = pd.to_datetime(comments_soe.index)
comments_ncr = source.non_conformances(data.site)

atmospheric_pressure_inspections = series_rounder(
    source.atmospheric_pressure_hydro_check_data(
        data.from_date, data.to_date, data.site
    ),
    "1min",
)
atmospheric_pressure_inspections = atmospheric_pressure_inspections[
    ~atmospheric_pressure_inspections["Value"].isna()
]
soe_check = series_rounder(
    source.soe_check_data(
        data,
        "Field Baro Pressure (HRC)",
    ),
    "1min",
)
check_data = [
    atmospheric_pressure_inspections,
    soe_check,
]

data.check_data = pd.concat([i for i in check_data if not i.empty])
data.check_data = data.check_data[
    ~data.check_data.index.duplicated(keep="first")
].sort_index()
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

with open("check_table.html", "w", encoding="utf-8") as file:
    data.check_data.to_html(file)
with open("quality_table.html", "w", encoding="utf-8") as file:
    data.quality_data.to_html(file)
with open("inspections_table.html", "w", encoding="utf-8") as file:
    comments_inspections.to_html(file)
with open("soe_table.html", "w", encoding="utf-8") as file:
    comments_soe.to_html(file)
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
        "calibration_table.html",
        "potential_processing_issues.html",
    ],
    encoding="utf-8",
    header=f"<h1>{data.site}</h1>\n<h2>From {data.from_date} to {data.to_date}</h2>",
)

merger.merge()
