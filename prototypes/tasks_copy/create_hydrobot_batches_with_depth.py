"""Copy tasks prototype."""

import os

import hydrobot.tasks as tasks

site_list_path = r"WaterTemperatureProcessing_Depth.csv"
destination_path = r"output_dump"
dsn_destination_path = destination_path + os.sep + r"test_home"

rainfall_config = tasks.csv_to_batch_dicts(site_list_path)

tasks.create_depth_hydrobot_batches(
    dsn_destination_path,
    destination_path,
    rainfall_config,
    create_directory=True,
)
