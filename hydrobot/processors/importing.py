"""Turn what a provider returns into the frames a Processor works on.

This is the PURE half of importing data: a provider's answer goes in, a frame
and a list of things worth reporting come out. Nothing here talks to a
server, a file or the Processor, so every rule can be tested with a small
table and no fakes.

The other half, asking the provider, lives on the Processor.
"""
from pandas.tseries.api import infer_freq

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from hydrobot import utils
from hydrobot.processors.frames import EMPTY_STANDARD_DATA
from hydrobot.providers.types import StandardData

# Codes for the processing issues raised while importing. They are kept as
# they were in the old Processor so that existing issue reports read
# the same.
NO_DATA_CODE = "MSD"
FREQUENCY_CODE = "IRR"


@dataclass(frozen=True)
class Note:
    """Something worth reporting as a processing issue.

    Importing does not report issues itself (it has no Processor to report
    to). It returns notes, and the Processor turns each into an issue. The
    fields are exactly the arguments of ``Processor.report_processing_issue``.
    """

    comment: str
    message_type: str  # "info", "warning" or "error"
    code: str | None = None
    series_type: str | None = None
    start_time: object = None
    end_time: object = None


@dataclass(frozen=True)
class StandardFrame:
    """A standard series ready to process, plus what happened building it."""

    data: pd.DataFrame
    # What the data was regularised to. None of it is empty or irregular.
    frequency: str | None
    notes: list[Note] = field(default_factory=list)

def standard_frame(
    standard: StandardData,
    *,
    measurement: str,
    frequency: str | None,
    infer_frequency: bool,
) -> StandardFrame:
    """Build the standard frame (``Raw``, ``Value``, ...) from a provider read.

    The provider has already scaled and typed the values, so nothing is
    divided or converted here. Only the first column is used. A standard
    series has one item, and the provider says so.

    Frequency, in order of preference:

    1.  ``frequency`` is given: the data is regularised to it, with NaN where
        points are missing.
    2.  Otherwise, if ``infer_frequency``: the most common gap between points
        is used. If there are too few points to tell (fewer than three), the
        data is left as it is and a warning says so.
    3.  Otherwise the data is irregular (rainfall, say) and left alone.

    Parameters
    ----------
    standard : StandardData
        What ``provider.get_standard`` returned. An empty read is normal and
        gives an empty frame plus an error note; it is the caller's job to
        decide what that means for the run.
    measurement : str
        The measurement that was asked for. Only used in messages.
    frequency : str or None
        A pandas frequency string such as ``"5min"``.
    infer_frequency : bool
        Whether to work out the frequency when none is given.
    """
    if standard.data.empty:
        origin = standard.metadata.get("origin", {})
        # Hilltop answers a misspelt measurement name with "no data", exactly
        # as it does for a quiet period, so the URL is the way to tell which
        # it was: paste it into a browser.
        where = origin.get("request_url", "unknown request")
        note = Note(
            comment=(
                f"No standard data found within specified date range. "
                f"Request: {where}"
            ),
            message_type="error",
            code=NO_DATA_CODE,
            series_type="Standard",
            start_time=origin.get("from_date"),
            end_time=origin.get("to_date"),
        )
        return StandardFrame(EMPTY_STANDARD_DATA.copy(), None, [note])

    values = standard.data.iloc[:, [0]]
    notes: list[Note] = []

    if frequency is not None:
        used = frequency
    elif infer_frequency and len(values) >= 3:
        used = utils.infer_frequency(values.index, method="mode")
        notes.append(Note(f"frequency inferred as {used}", "info", FREQUENCY_CODE))
    elif infer_frequency:
        used = None
        notes.append(
            Note(
                f"Only {len(values)} point(s) for {measurement}: too few to infer "
                "a frequency (needs 3). Left as it is.",
                "warning",
                FREQUENCY_CODE,
            )
        )
    else:
        used = None
        notes.append(
            Note(
                "No frequency provided and infer_frequency is set to False. "
                f"Assuming irregular data for {measurement}.",
                "info",
                FREQUENCY_CODE,
            )
        )

    if used is not None:
        values = values.asfreq(used, fill_value=np.nan)

    # Build the frame the same way the old Processor did, so that its shape
    # (columns, dtypes, the index called "Time") is exactly what the rest of
    # the processor expects.
    frame = EMPTY_STANDARD_DATA.copy()
    frame["Raw"] = values.iloc[:, 0]
    frame["Value"] = frame["Raw"]
    return StandardFrame(frame, used, notes)
