"""Prototype script."""

import hydrobot.tasks as tasks

destination_path = r"output_dump"

rainfall_config = tasks.csv_to_batch_dicts(r"SoilTemperatureProcessing.csv")

tasks.create_mass_hydrobot_batches(
    destination_path + r"/test_home",
    destination_path,
    rainfall_config,
    create_directory=True,
)
