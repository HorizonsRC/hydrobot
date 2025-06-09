"""Copy tasks prototype."""

import hydrobot.tasks as tasks

data_family = "Rainfall"
destination_path = r"C:\Users\SIrvine\PycharmProjects\hydro-processing-tools\prototypes\tasks_copy\output_dump"

test_config = [
    {
        "site": "Manawatu at Teachers College",
        "data_family": data_family,
        "standard_measurement_name": "Water Temperature [Dissolved Oxygen sensor]",
    },
    {
        "site": "Manawatu at Hopelands",
        "data_family": data_family,
        "standard_measurement_name": "Water Temperature [Dissolved Oxygen sensor]",
    },
]

rainfall_config = tasks.csv_to_batch_dicts(
    r"C:\Users\SIrvine\PycharmProjects\hydro-processing-tools\prototypes\tasks_copy\RainfallReprocessing.csv"
)

tasks.create_mass_hydrobot_batches(
    destination_path + r"\test_home", destination_path, rainfall_config
)
