"""Copy tasks prototype."""

import os

import hydrobot.tasks as tasks

destination_path = r"output_dump"

rainfall_config = tasks.csv_to_batch_dicts(r"SoilMoistureDepthProcessing.csv")

tasks.create_depth_hydrobot_batches(
    destination_path + f"{os.sep}test_home",
    destination_path,
    rainfall_config,
    create_directory=True,
)
