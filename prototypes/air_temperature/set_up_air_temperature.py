"""Air Temperature script."""

import os

import hydrobot.tasks as tasks

destination_path = r"AirTemperature/"

config = tasks.csv_to_batch_dicts(r"AirTemperatureProcessing.csv")
depth_config = tasks.csv_to_batch_dicts(r"AirTemperatureDepthProcessing.csv")

os_sep = os.sep

tasks.create_mass_hydrobot_batches(
    destination_path + f"{os_sep}at_home",
    destination_path,
    config,
    create_directory=True,
)

tasks.create_depth_hydrobot_batches(
    destination_path + f"{os_sep}at_depth_home",
    destination_path,
    depth_config,
    create_directory=True,
)
