"""Missing record script."""

import yaml

with open("script_config.yaml") as file:
    config = yaml.safe_load(file)


def report_missing_record(site, measurement, start, end):
    """Reports minutes missing."""
    pass


for site in config["sites"]:
    for meas in config["measurements"]:
        report_missing_record(site, meas, config["start"], config["end"])
