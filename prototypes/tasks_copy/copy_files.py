"""Copy tasks prototype."""

import hydrobot.tasks as tasks

data_family = "Water Temperature"
destination_path = r"C:\Users\SIrvine\PycharmProjects\hydro-processing-tools\prototypes\tasks_copy\output_dump"

test_config = [
    {"site": "Manawatu at Teachers College", "data_family": data_family},
    {"site": "Manawatu at Hopelands", "data_family": data_family},
]

tasks.create_mass_hydrobot_batches(
    destination_path + r"\test_home", destination_path, test_config
)
