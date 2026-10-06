from typing import Any
from pydantic import BaseModel
import pandas as pd


class DataProviderError(Exception):
    """Base exception for provider failures."""


class StandardData(BaseModel):
    data: pd.DataFrame
    metadata: dict[str, Any] = {}


class CheckData(BaseModel):
    data: pd.DataFrame
    metadata: dict[str, Any] = {}
