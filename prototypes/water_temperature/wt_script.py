"""Script to run through a processing task for Water Temperature."""

import pandas as pd

import hydrobot.config.horizons_source as source
from hydrobot.data_acquisition import (
    import_inspections,
    import_ncr,
    import_prov_wq,
)
from hydrobot.filters import trim_series
from hydrobot.htmlmerger import HtmlMerger
from hydrobot.processor import Processor
from hydrobot.utils import merge_all_comments

#######################################################################################
# Reading configuration from config.yaml
#######################################################################################
data, ann = Processor.from_config_yaml("wt_config.yaml")

#######################################################################################
# Importing all check data
#######################################################################################
check_col = "Temp Check"
logger_col = "Temp Logger"

inspections = import_inspections(
    "WaterTemp_Inspections.csv", check_col=check_col, logger_col=logger_col
)
prov_wq = import_prov_wq(
    "WaterTemp_ProvWQ.csv",
    check_col=check_col,
    logger_col=logger_col,
    use_for_qc=True,
)
ncrs = import_ncr("WaterTemp_non-conformance_reports.csv")

inspections_no_dup = inspections.drop(data.check_data.index, errors="ignore")
prov_wq_no_dup = prov_wq.drop(data.check_data.index, errors="ignore")

all_checks_list = [data.check_data, inspections, prov_wq]
all_checks_list = [i for i in all_checks_list if not i.empty]
all_checks = pd.concat(all_checks_list).sort_index()

all_checks = all_checks.loc[
    (all_checks.index >= data.from_date) & (all_checks.index <= data.to_date)
]

data_check_list = [data.check_data, inspections_no_dup, prov_wq_no_dup]
data_check_list = [i for i in data_check_list if not i.empty]
data.check_data = pd.concat(data_check_list).sort_index()

data.check_data = data.check_data.loc[
    (data.check_data.index >= pd.Timestamp(data.from_date))
    & (data.check_data.index <= pd.Timestamp(data.to_date))
]

all_comments = merge_all_comments(data.check_data, prov_wq, inspections, ncrs)

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
    all_comments.to_html(file)
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
