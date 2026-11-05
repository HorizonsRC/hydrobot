"""Prototype script."""

import os

import hydrobot.tasks as tasks

site_list_path = r"WaterTemperatureProcessing.csv"
destination_path = r"output_dump"
dsn_destination_path = destination_path + os.sep + r"hydrobot"

config_dicts = tasks.csv_to_batch_dicts(site_list_path)

os_sep = os.sep

tasks.create_mass_hydrobot_batches(
    dsn_destination_path,
    destination_path,
    config_dicts,
    create_directory=True,
)
