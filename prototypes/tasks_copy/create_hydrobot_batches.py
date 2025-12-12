"""Prototype script."""

import os

import hydrobot.tasks as tasks

destination_path = r"output_dump"

rainfall_config = tasks.csv_to_batch_dicts(r"WaterTemperatureProcessing.csv")

os_sep = os.sep

tasks.create_mass_hydrobot_batches(
    destination_path + f"{os_sep}test_home",
    destination_path,
    rainfall_config,
    create_directory=True,
)
