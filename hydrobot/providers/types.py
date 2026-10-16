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
