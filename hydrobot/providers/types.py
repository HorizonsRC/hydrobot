"""The shapes of what providers hand back.

Every data read returns one of the models below: a table of data plus a
``metadata`` dict that describes it (units, formats, and where it came from).
"""

from datetime import datetime
from typing import Any, TypedDict

import pandas as pd
from pydantic import BaseModel, ConfigDict



class DataProviderError(Exception):
    """Base exception for provider failures."""


# The models below hold DataFrames, which pydantic doesn't know how to check,
# so each one has to opt in with arbitrary_types_allowed.


class StandardData(BaseModel):
    """A standard (telemetry) series, with item metadata."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    data: pd.DataFrame
    metadata: dict[str, Any] = {}


class CheckData(BaseModel):
    """Check data: one column per item (check value, recorder time, ...)."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    data: pd.DataFrame
    metadata: dict[str, Any] = {}


class QualityData(BaseModel):
    """A quality series: one column of integer quality codes, by time."""
    model_config = ConfigDict(arbitrary_types_allowed=True)

    data: pd.DataFrame
    metadata: dict[str, Any] = {}


class SiteInfo(BaseModel):
    """What hydrobot needs to know about a site, whatever the data source."""

    # Short code for the site (e.g. "TCO"), used in file names. Where a
    # council stores it is the provider's business.
    code: str
    # Everything else the source returned, unprocessed, for later use.
    metadata: dict[str, Any] = {}


class Origin(TypedDict):
    """Where a piece of data came from. Every data read records one.

    It lives in the result's ``metadata["origin"]``, so downstream code (and
    eventually drilldown plots) can answer "where did this come from?".
    It is recoded even when the read found nothing: "we asked, and got
    nothing" is itself worth knowing.
    """

    provider: str  # which provider implementation, e.g. "horizons-hilltop"
    source_tag: str  # short tag for plots/grouping, e.g. "HTP"
    base_url: str  # the server, with any credentials or query removed
    hts: str  # the HTS (data file) asked, e.g. "RawLoggerNet.hts"
    site: str
    measurement: str
    ts_type: str  # e.g. "StdSeries", "StdQualSeries", "CheckSeries"
    from_date: datetime  # ... and the range that was requested
    to_date: datetime
    retrieved_at: datetime  # when the provider asked the server
    request_url: str  # the url request sent to the server.
