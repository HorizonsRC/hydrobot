"""
Meant to give URLs for hilltop server calls.

Maybe useful for debugging?
"""

import hilltoppy
import yaml

with open("config.yaml") as yaml_file:
    processing_parameters = yaml.safe_load(yaml_file)

url = hilltoppy.utils.build_url(
    processing_parameters["base_url"], processing_parameters["hts_filename"], "SiteList"
)

print("Site list")
print(url)

url = hilltoppy.utils.build_url(
    processing_parameters["base_url"],
    processing_parameters["hts_filename"],
    "CollectionList",
)

print("Collection list")
print(url)

# measurement: str = None, collection: str = None,
# from_date: str = None, to_date: str = None, location: Union[str, bool] = None, site_parameters: List[str] = None,
# agg_method: str = None, agg_interval: str = None, alignment: str = None, quality_codes: bool = False, tstype: str
# = None, response_format: str = None, units: bool = None
url = hilltoppy.utils.build_url(
    processing_parameters["base_url"],
    processing_parameters["hts_filename"],
    "MeasurementList",
    processing_parameters["site"],
)

print("Measurement list")
print(url)

url = hilltoppy.utils.build_url(
    processing_parameters["base_url"],
    processing_parameters["hts_filename"],
    "SiteInfo",
    processing_parameters["site"],
)

print("Site Info")
print(url)


url = hilltoppy.utils.build_url(
    processing_parameters["base_url"],
    processing_parameters["hts_filename"],
    "GetData",
    processing_parameters["site"],
    measurement=processing_parameters["standard_measurement_name"],
    tstype="Standard",
    from_date=processing_parameters["from_date"],
    to_date=processing_parameters["to_date"],
)

print("Standard data")
print(url)

url = hilltoppy.utils.build_url(
    processing_parameters["base_url"],
    processing_parameters["hts_filename"],
    "GetData",
    processing_parameters["site"],
    measurement=processing_parameters["standard_measurement_name"],
    tstype="Standard",
)

print("If you want all the data")
print(url)

print("If you just want the most recent data point, lose the TimeInterval, i.e.")
print(url[:-30])

url = hilltoppy.utils.build_url(
    processing_parameters["base_url"],
    processing_parameters["hts_filename"],
    "GetData",
    processing_parameters["site"],
    measurement=processing_parameters["check_measurement_name"],
    tstype="Check",
    from_date=processing_parameters["from_date"],
    to_date=processing_parameters["to_date"],
)

print("Check data")
print(url)

url = hilltoppy.utils.build_url(
    processing_parameters["base_url"],
    processing_parameters["hts_filename"],
    "GetData",
    processing_parameters["site"],
    measurement=processing_parameters["quality_measurement_name"],
    tstype="Quality",
    from_date=processing_parameters["from_date"],
    to_date=processing_parameters["to_date"],
)

print("Quality data")
print(url)
