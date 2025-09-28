"""Prototype script."""

import hydrobot.tasks as tasks

destination_path = r"C:\Users\SIrvine\PycharmProjects\hydro-processing-tools\prototypes\tasks_copy\output_dump"

rainfall_config = tasks.csv_to_batch_dicts(
    r"C:\Users\SIrvine\PycharmProjects\hydro-processing-tools\prototypes\tasks_copy\data_source_proto.csv"
)

tasks.create_depth_hydrobot_batches(
    destination_path + r"\test_home",
    destination_path,
    rainfall_config,
    create_directory=True,
)
