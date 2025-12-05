"""Soil Moisture script."""

import os

import hydrobot.tasks as tasks

destination_path = r"SoilMoisture/"

config = tasks.csv_to_batch_dicts(r"SoilMoistureProcessing.csv")
depth_config = tasks.csv_to_batch_dicts(r"SoilMoistureDepthProcessing.csv")

os_sep = os.sep

tasks.create_mass_hydrobot_batches(
    destination_path + f"{os_sep}sm_home",
    destination_path,
    config,
    create_directory=True,
)

tasks.create_depth_hydrobot_batches(
    destination_path + f"{os_sep}sm_depth_home",
    destination_path,
    depth_config,
    create_directory=True,
)
