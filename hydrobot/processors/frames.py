"""The empty frames that a Processor's data starts from.

Each frame has a fixed set of columns that the rest of the Processor relies
on, and a time index called ``Time``. They live in their own module so that
both the Processor and the helpers that build its frames can import them
without importing each other.

Always ``.copy()`` one before using it: they are shared, module-level objects.
"""

import pandas as pd

EMPTY_STANDARD_DATA = pd.DataFrame(
    columns=[
        "Time",
        "Raw",
        "Value",
        "Changes",
        "Remove",
    ]
).set_index("Time")


EMPTY_CHECK_DATA = pd.DataFrame(
    columns=[
        "Time",
        "Raw",
        "Value",
        "Changes",
        "Recorder Time",
        "Comment",
        "Source",
        "QC",
    ]
).set_index("Time")
EMPTY_QUALITY_DATA = pd.DataFrame(
    columns=[
        "Time",
        "Raw",
        "Value",
        "Code",
        "Details",
    ]
).set_index("Time")
