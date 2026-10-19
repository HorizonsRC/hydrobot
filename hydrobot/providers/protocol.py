from typing import Protocol
from datetime import datetime

from hydrobot.providers.types import CheckData, SiteInfo, StandardData

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

    # def get_check(
    #     self,
    #     site: str,
    #     measurement: str,
    #     from_date: datetime,
    #     to_date: datetime,
    # ) -> CheckData:
    #     """Return check data and associated metadata."""
    #     ...

    def last_processed_time(
        self,
        site: str,
        measurement: str
    ) -> datetime | None:
        """Return the timestamp from which new processing should resume.

        None if this series has never been archived.
        """
        ...

    def get_site_info(self, site: str) -> SiteInfo:
        """Return information about a site, including its short code."""
        ...
