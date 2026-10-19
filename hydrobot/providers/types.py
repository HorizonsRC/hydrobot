from typing import Any
from pydantic import BaseModel, ConfigDict
import pandas as pd


class DataProviderError(Exception):
    """Base exception for provider failures."""


class StandardData(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    data: pd.DataFrame
    metadata: dict[str, Any] = {}


class CheckData(BaseModel):
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
