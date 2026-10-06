from typing import Protocol
from datetime import datetime

from hydrobot.providers.types import CheckData, StandardData

class DataProvider(Protocol):
    """Provides processor-ready data."""

    def get_standard(
        self,
        site: str,
        measurement: str,
        from_date: datetime,
        to_date: datetime

    ) -> StandardData:
        """Return standard data and associated metadata."""
        ...

    def get_check(
        self,
        site: str,
        measurement: str,
        from_date: datetime,
        to_date: datetime,
    ) -> CheckData:
        """Return check data and associated metadata."""
        ...
