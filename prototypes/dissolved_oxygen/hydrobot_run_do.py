"""Script to run through a processing task for Dissolved Oxygen."""

import numpy as np
import pandas as pd

import hydrobot.config.horizons_source as source
from hydrobot.filters import trim_series
from hydrobot.htmlmerger import HtmlMerger
from hydrobot.hydrobot_initialiser import initialise_hydrobot_from_yaml
from hydrobot.processor import EMPTY_CHECK_DATA
from hydrobot.utils import series_rounder

checks_to_manually_ignore = []
data_sections_to_delete = []

#######################################################################################
# Reading configuration from config.yaml
#######################################################################################
data, ann = initialise_hydrobot_from_yaml("hydrobot_yaml_config_do.yaml")

for bad_section in data_sections_to_delete:
    data.standard_data.loc[
        (data.standard_data.index > bad_section[0])
        & (data.standard_data.index < bad_section[1]),
        "Value",
    ] = np.nan

#######################################################################################
# Importing all check data
#######################################################################################
comments_inspections = source.dissolved_oxygen_hydro_inspections(
    data.from_date, data.to_date, data.site
)
if data.check_hts_filename is not None:
    comments_soe = data.get_measurement_dataframe("Field DO Saturation (HRC)", "check")
    comments_soe.index = pd.to_datetime(comments_soe.index)
else:
    comments_soe = pd.DataFrame()
comments_ncr = source.non_conformances(data.site)

dissolved_oxygen_inspections = series_rounder(
    source.dissolved_oxygen_hydro_check_data(data.from_date, data.to_date, data.site),
    "1min",
)
dissolved_oxygen_inspections = dissolved_oxygen_inspections[
    ~dissolved_oxygen_inspections["Value"].isna()
]

depth_check = pd.DataFrame()
soe_check = pd.DataFrame()
if data.depth:
    depth_check = data.interpolate_depth_profiles(
        data.depth / 1000.0, "Dissolved Oxygen (Depth Profile)"
    )
    depth_check = source.convert_check_series_to_check_frame(depth_check, "DPF")
elif data.check_hts_filename is not None:
    soe_check = series_rounder(
        source.soe_check_data(
            data,
            "Field DO Saturation (HRC)",
        ),
        "1min",
    )

soe_check = soe_check
check_data = [
    dissolved_oxygen_inspections,
    soe_check,
    depth_check,
]
if [i for i in check_data if not i.empty]:
    data.check_data = pd.concat([i for i in check_data if not i.empty])
    data.check_data = data.check_data[
        ~data.check_data.index.duplicated(keep="first")
    ].sort_index()
else:
    # no check
    data.check_data = EMPTY_CHECK_DATA.copy()
data.check_data["Value"] = trim_series(data.check_data["Value"], data.to_date)

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
data.remove_spikes()

#######################################################################################
# DO specific operation
#######################################################################################
data.correct_do()

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
if not data.check_data.empty:
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
# Delete any QC100 data that may have snuck in
#######################################################################################
data.remove_qc100_data()

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

with open("potential_processing_issues.html", "w", encoding="utf-8") as file:
    file.write("<p>Hydrobot Run Issues</p>")
    data.processing_issues.to_html(file)
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
    comments_inspections.to_html(file)
with open("soe_table.html", "w", encoding="utf-8") as file:
    file.write("<p>State of Environment</p>")
    comments_soe.to_html(file)
with open("ncr_table.html", "w", encoding="utf-8") as file:
    file.write("<p>Non-conformance reports</p>")
    comments_ncr.to_html(file)
with open("calibration_table.html", "w", encoding="utf-8") as file:
    file.write("<p>Calibrations</p>")
    source.calibrations(
        data.site, measurement_name=data.standard_measurement_name
    ).to_html(file)


merger = HtmlMerger(
    [
        "pyplot.html",
        "potential_processing_issues.html",
        "check_table.html",
        "inspections_table.html",
        "soe_table.html",
        "ncr_table.html",
        "calibration_table.html",
        "quality_table.html",
    ],
    encoding="utf-8",
    header=f"<h1>{data.site}</h1>\n<h2>{data.standard_measurement_name}</h2>\n<h2>From {data.from_date} to {data.to_date}</h2>",
)

merger.merge()
