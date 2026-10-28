"""The DataProvider protocol: what hydrobot needs from any data source.

A provider is everything source-specific. The rest of hydrobot asks it
questions in hydrobot's own vocabulary and never sees Hilltop, SQL or
whatever sits behind it. Each method's docstring is a CONTRACT: every
provider must behave exactly as described, including in the empty cases.
"""


from typing import Protocol
from datetime import datetime

from hydrobot.providers.types import CheckData, QualityData, SiteInfo, StandardData



class DataProvider(Protocol):
    """Provides processor-ready data."""

    def get_standard(
        self,
        site: str,
        measurement: str,
        from_date: datetime,
        to_date: datetime

    ) -> StandardData:
        """Return standard data and associated metadata.

        Contract every provider must follow:

        *   Data found: returned with metadata keys ``item_name``,
            ``item_format``, ``divisor``, ``units`` and ``number_format``.
        *   Every read records ``metadata["origin"]`` (see ``Origin`` in
            types.py): where the data came from and when.
        *   No data at all in the range: return EMPTY data and metadata. Not an
            error; the caller reports it.
        *   Data returned but not this measurement (almost certainly a wrong
            name): raise DataProviderError.
        *   The data is already scaled by its divisor; callers must not
            divide again.
        """
        ...


    def get_quality(
        self,
        site: str,
        measurement: str,
        from_date: datetime,
        to_date: datetime,
    ) -> QualityData:
        """Return the quality-code series for a standard measurement.

        Contract:

        *   One column of integer quality codes, indexed by time.
        *   A measurement with no quality series (normal for unprocessed data) gives
            EMPTY data, never an error.
        *   Raise DataProviderError only if the source returns more than one
            matching series, since then we can't know which is right.
        """
        ...

    def get_check(
        self,
        site: str,
        measurement: str,
        from_date: datetime,
        to_date: datetime,
    ) -> CheckData:
        """Return check datta, with one column per item, and its metadata.

        Contract:

        *   ``data`` has one column per item, named by item name (e.g. the check
            value, "Recorder Time", "Comment"), already typed and scaled.
            Callers must not re-apply formats or divisors.
        *   ``metadata["items"]`` lists each item's ``item_name``,
            ``item_format``, ``divisor``, ``units`` and ``number_format``, in
            the same order as the columns of ``data``.
            ``metadata["item_format"]`` is the data-source-level item format.
        *   ``metadata["origin"]`` is always set (see ``Origin``).
        *   No matching check series (or no data in range): EMPTY data (the
            metadata holds only the origin), not an error; the caller reports it.
        *   Raise DataProviderError only if more than one series matches.
        *   Only ``measurement`` is searched for; there is no fallback to
            another name.
        """
        ...

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
