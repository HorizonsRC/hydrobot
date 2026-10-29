"""Horizons' data provider: reads Hilltop data through whurl.

Everything Horizons-specific lives here: how Hilltop names things, which HTS
file holds what, and which SiteInfo field holds a site's code. The rest of
hydrobot only sees the DataProvider protocol (see protocol.py)
"""

import re
from collections.abc import Callable
from datetime import datetime
from urllib.parse import urlsplit, urlunsplit

import pandas as pd
from pydantic import BaseModel
from whurl.client import HilltopClient
from whurl.exceptions import HilltopError
from whurl.schemas.requests import GetDataRequest

from hydrobot.orchestration.resume import resume_point
from hydrobot.providers.types import (
    CheckData,
    DataProviderError,
    Origin,
    QualityData,
    SiteInfo,
    StandardData,
)



class HorizonsProviderConfig(BaseModel):
    """Mirrors the ``provider_params`` block of the YAML config."""

    base_url: str
    standard_hts_filename: str
    check_hts_filename: str
    # The archive is optional: only last_processed_time needs it (so far).
    archive_base_url: str | None = None
    archive_standard_hts_filename: str | None = None
    archive_check_hts_filename: str | None = None
    # Which Hilltop SiteInfo fields holds the site's short code at Horizons.
    # (Hilltop's screens say "Second Synonym"; in the XML it is this tag.)
    site_code_field: str = "SecondSynonym"



class HorizonsProvider:
    """Hilltop-backed provider for Horizons via whurl.

    Deliberately does NOT subclass DataProvider: a subclass would inherit the
    Protocol's ``...`` bodies, so a forgotten method would silently return
    ``None``. tests/test_providers/test_horizons.py checks conformance instead.
    """

    # Recorded in every read's origin.
    PROVIDER_NAME = "horizons-hilltop"
    SOURCE_TAG = "HTP"  # the short tag plots group check data by

    # where "now" comes from. A class attribute so tests can replace it.
    _clock: Callable[[], datetime] = staticmethod(datetime.now)


    def __init__(
        self,
        config: HorizonsProviderConfig,
    ):
        self.config = config
        # One client per HTS file: standard and check data live in different
        # files, and the archive is a different server again.
        self.client = HilltopClient(
            base_url=config.base_url,
            hts_endpoint=config.standard_hts_filename,
        )
        self.check_client = HilltopClient(
            base_url=config.base_url,
            hts_endpoint=config.check_hts_filename,
        )
        self.archive_client = None
        if config.archive_base_url and config.archive_standard_hts_filename:
            self.archive_client = HilltopClient(
                base_url=config.archive_base_url,
                hts_endpoint=config.archive_standard_hts_filename,
            )
        self.site_code_field = config.site_code_field

    # -------------------------------------------------------------------------
    # Lifetime of the connections
    # -------------------------------------------------------------------------
    # The provider opens its HTTP clients once and keeps them for its whole
    # life, so any number of reads can reuse them. Do NOT wrap each read in
    # ``with client:``. Leaving that block CLOSES the client for good, and the
    # next read then fails with "client has been closed". Instead, whoever
    # creates the provider decides when it is finished:
    #
    #   with HorizonsProvider(config) as provider:
    #       ...     # As many reads as you like

    def close(self) -> None:
        """Close every connection. The provider can't be used afterwards."""
        for client in (self.client, self.check_client, self.archive_client):
            if client is not None:
                client.close()

    def __enter__(self) -> "HorizonsProvider":
        return self

    def __exit__(self, *exc) -> None:
        self.close()


    # -------------------------------------------------------------------------
    # Data reads: standard, quality, check
    # -------------------------------------------------------------------------

    def get_standard(
        self,
        site: str,
        measurement: str,
        from_date: datetime,
        to_date: datetime,
    ) -> StandardData:
        """Return standard data and associated metadata.

        Three outcomes, kept distinct on purpose:

        *   Data found: returned with its metadata.
        *   No data at all in the requested range: returned EMPTY (an empty
            DataFrame and empty metadata), not an error. A quiet period is
            normal, and the caller decides how to report it.
        *   Data came back but none of it is this measurement: an error that
            lists what WAS available, since that means a wrong name.

        The data has already had its Hilltop divisor applied (by whurl). The
        ``divisor`` in the metadata is for information only: don't divide again.
        """

        response, request_url = self._fetch(
            self.client,
            site=site,
            measurement=measurement,
            from_datetime=from_date,
            to_datetime=to_date,
            ts_type="StdSeries",
        )

        origin = self._origin(
            self.client,
            request_url,
            site=site,
            measurement=measurement,
            ts_type="StdSeries",
            from_date=from_date,
            to_date=to_date,
        )

        # No data at all: either the server said so (no response), or it sent
        # an empty reply. Either way, report empty and let the caller decide.
        if response is None or not response.measurements:
            return StandardData(data=pd.DataFrame(), metadata={"origin": origin})
        returned = response.measurements

        found = _matching_series(response, measurement, "StdSeries", site)
        if found is None:
            raise DataProviderError(
                f"Standard data not found under name {measurement!r}."
                f"Available data sources are: {[m.data_source.name for m in returned]}."
            )

        item = found.data_source.item_info[0]
        metadata = {
            "item_name": item.item_name,
            "item_format": item.item_format,
            # Hilltop leaves the divisor out when it is 1.
            "divisor": 1 if item.divisor is None else item.divisor,
            "units": item.units,
            "number_format": item.format,
            "origin": origin,
        }
        return StandardData(data=found.data.timeseries, metadata=metadata)


    def get_quality(
        self,
        site: str,
        measurement: str,
        from_date: datetime,
        to_date: datetime,
    ) -> QualityData:
        """Return the quality-code series for a standard measurement.

        Quality lives alongside the standard data, in the same HTS. Having no
        quality series is normal (means nothing has been processed yet), so
        that returns empty data rather than raising.
        """
        response, request_url = self._fetch(
            self.client,
            site=site,
            measurement=measurement,
            from_datetime=from_date,
            to_datetime=to_date,
            ts_type="StdQualSeries",
        )

        origin = self._origin(
            self.client,
            request_url,
            site=site,
            measurement=measurement,
            ts_type="StdQualSeries",
            from_date=from_date,
            to_date=to_date,
        )

        found = _matching_series(response, measurement, "StdQualSeries", site)
        if found is None:
            return QualityData(data=pd.DataFrame(), metadata={"origin": origin})

        df = found.data.timeseries
        if df.shape[1] != 1:
            raise DataProviderError(
                f"Expected a single quality column for {site!r} / {measurement!r}; "
                f" got {list(df.columns)}."
            )

        return QualityData(data=df.astype(int), metadata={"origin": origin})

    def get_check(
        self,
        site: str,
        measurement: str,
        from_date: datetime,
        to_date: datetime,
    ) -> CheckData:
        """Return check data (one column per item) with item metadata.

        whurl has already typed each column and applied divisors, by item
        name. Only ``measurement`` is searched for: the run config names the
        check measurement exactly, so there's no fallback to another name.
        """
        response, request_url = self._fetch(
            self.check_client,
            site=site,
            measurement=measurement,
            from_datetime=from_date,
            to_datetime=to_date,
            ts_type="CheckSeries",
        )

        origin = self._origin(
            self.check_client,
            request_url,
            site=site,
            measurement=measurement,
            ts_type="CheckSeries",
            from_date=from_date,
            to_date=to_date,
        )

        found = _matching_series(response, measurement, "CheckSeries", site)
        if found is None:
            return CheckData(data=pd.DataFrame(), metadata={"origin": origin})

        # Columns come out in item-NUMBER order, but a resopnse may list its
        # ItemInfo blocks in any order, so sort to match the columns.
        items = sorted(found.data_source.item_info, key=lambda i: i.item_number)
        metadata = {
            "item_format": found.data_source.item_format,
            "origin": origin,
            "items": [
                {
                    "item_name": i.item_name,
                    "item_format": i.item_format,
                    "divisor": 1 if i.divisor is None else i.divisor,
                    "units": i.units,
                    "number_format": i.format,
                }
                for i in items
            ],
        }
        return CheckData(data=found.data.timeseries, metadata=metadata)


    # -------------------------------------------------------------------------
    # Where did the last processing run get to?
    # -------------------------------------------------------------------------


    def last_processed_time(self, site: str, measurement: str) -> datetime | None:
        """Return when processing should resume, or None if never archived.

        A GetData with no time range returns only the latest point. So we ask
        for the latest quality entry first, then fetch the standard data (with
        quality) form that time on, so trailing points that were copied up
        without being processed can be recognised and ignored.
        """
        if self.archive_client is None:
            raise DataProviderError(
                "last_processed_time needs archive_base_url and "
                "archive_standard_hts_filename in provider_params."
            )

        archive = self.archive_client
        qual_response, _ = self._fetch(
            archive, site=site, measurement=measurement, ts_type="StdQualSeries"
        )
        found_qual = _matching_series(qual_response, measurement, "StdQualSeries", site)
        qual = _quality_series(
            found_qual.data.timeseries if found_qual else pd.DataFrame()
        )

        from_kwargs = {}
        if not qual.empty:
            from_kwargs["from_datetime"] = qual.index.max().to_pydatetime()

        std_response, _ = self._fetch(
            archive,
            site=site,
            measurement=measurement,
            ts_type="StdSeries",
            show_quality="Yes",
            **from_kwargs,
        )
        found_std = _matching_series(std_response, measurement, "StdSeries", site)
        std = found_std.data.timeseries if found_std else pd.DataFrame()

        if not std.empty:
            if "Quality" not in std.columns:
                raise DataProviderError(
                    "Archive standard data has no 'Quality' column; "
                    f"got {list(std.columns)}."
                )
            # whurl delivers quality as text ("600"), but resume_point needs
            # numbers. Anything blank or unreadable becomes NaN, which counts as
            # "no quality" (unprocessed), the safe reading.
            std = std.assign(Quality=pd.to_numeric(std["Quality"], errors="coerce"))

        result = resume_point(std, qual)

        return None if result is None else result.to_pydatetime()

    # -------------------------------------------------------------------------
    # Site infomation
    # -------------------------------------------------------------------------

    def get_site_info(self, site: str) -> SiteInfo:
        """Return site info, with the short code read from Hilltop's SiteInfo.

        Which SiteInfo field holds the code is Horizons-specific, so it is
        configurable (``site_code_field``, default "SecondSynonym").
        """
        response = self.client.get_site_info(site=site)

        matches = [s for s in response.site if s.name == site]
        if len(matches) != 1:
            raise DataProviderError(
                f"Expected exactly one SiteInfo entry for {site!r}; "
                f"got {len(matches)}."
            )

        info = matches[0].info

        code = info.get(self.site_code_field)
        if code is None or not str(code).strip():
            raise DataProviderError(
                f"SiteInfo for {site!r} has no usable {self.site_code_field!r} "
                f"field. Fields available: {sorted(info)}."
            )
        return SiteInfo(code=str(code).strip(), metadata=info)


    # -------------------------------------------------------------------------
    # Internals
    # -------------------------------------------------------------------------

    def _fetch(self, client, **kwargs):
        """Make a GetData request. Returns ``(response, request_url)``.

        Hilltop reports an empty range ("No data from X to Y") as an ERROR
        document (xml response), which whurl raises as an exception. For us
        that is not an error: it is just "no data", so ``response`` is None.
        Quality is event-based, so a quiet few days with no entries is
        completely normal.

        Any other Hilltop error is a genuine problem. It is re-raised as a
        DataProviderError (keeping the original message), so callers never
        need to know whurl's exception types.

        The URL is the request actually made when there is a response. When
        there was none, whurl's error doesn't carry the URL, so we ask whurl's
        own GetDataRequest to build the one it would have used.
        """
        try:
            response = client.get_data(**kwargs)
        except HilltopError as error:
            if _NO_DATA.search(str(error)):
                return None, _request_url_for(client, kwargs)
            raise DataProviderError(
                f"Hilltop returned an error for {kwargs.get('site')!r} / "
                f"{kwargs.get('measurement')!r}: {error}"
            ) from error
        return response, response.request.gen_url()

    def _origin(
        self,
        client,
        request_url: str,
        *,
        site: str,
        measurement: str,
        ts_type: str,
        from_date: datetime,
        to_date: datetime,
    ) -> Origin:
        """Describe a read: which server and HTS, what was asked, and when.

        whurl attaches the request it built to every response, so the exact
        URL comes from ``response.request.gen_url()``.
        """
        return Origin(
            provider=self.PROVIDER_NAME,
            source_tag=self.SOURCE_TAG,
            base_url=_public_url(client.base_url),
            hts=client.hts_endpoint,
            request_url=_public_request_url(request_url),
            site=site,
            measurement=measurement,
            ts_type=ts_type,
            from_date=from_date,
            to_date=to_date,
            retrieved_at=self._clock(),
        )



# -----------------------------------------------------------------------------
# Helpers (plain functions: they don't need the provider)
# -----------------------------------------------------------------------------



def _timeseries(response, site: str, measurement: str) -> pd.DataFrame:
    """The single matching timeseries in a response; empty if none."""
    found = [m for m in response.measurements if m.data_source.name == measurement]
    if len(found) > 1:
        raise DataProviderError(
            f"Multiple measurement returned for {site} and {measurement}."
        )
    return found[0].data.timeseries if found else pd.DataFrame()


def _quality_series(df: pd.DataFrame) -> pd.Series:
    """A StdQualSeries frame (one column of quality codes) as a Series."""
    if df.empty:
        return pd.Series(dtype=float, name="Quality")
    if df.shape[1] != 1:
        raise DataProviderError(
            f"Expected a single quality column; got {list(df.columns)}."
        )
    return df.iloc[:, 0].astype(float).rename("Quality")


def _split_measurement_name(measurement: str) -> tuple[str, str]:
    """Split a Hilltop ``Item [Data Source]`` name into (item, data source).

    With no brackets the data source has the same name as the item. (Same
    rule as ``hydrobot.utils.measurement_datasource_splitter``, kept here so
    the provider doesn't depend on the legacy utils module.)
    """
    match = re.search(r"([^\[\n]+)(\[(.+)\])?", measurement)
    if match is None:
        raise DataProviderError(f"Can't read measurement name {measurement!r}.")
    item = match.group(1).strip(" ")
    data_source = match.group(3)

    return item, (item if data_source is None else data_source)


def _matching_series(response, measurement: str, ts_type: str, site: str):
    """The one series in ``response`` of this type and data source, or None.

    Hilltop names can be ``Item [Data Source]``; the data source is what the
    server reports, so that is what is matched. Raises if more than one
    series matches, since there's no way to know which is right.
    """
    if response is None:
        return None
    _, data_source_name = _split_measurement_name(measurement)
    found = [
        m
        for m in (response.measurements or [])
        if m.data_source.name == data_source_name
        and m.data_source.ts_type == ts_type
        and m.data.timeseries is not None
    ]
    if len(found) > 1:
        raise DataProviderError(
            f"Multiple {ts_type} series returned for {site!r} / {measurement!r}."
        )
    return found[0] if found else None


def _strip_userinfo(netloc: str) -> str:
    """``user:password@host:port`` -> ``host:port``."""
    return netloc.rpartition("@")[2]


def _public_url(url: str) -> str:
    """The server address with anything sensitive removed.

    A base URL may carry a username and password, or a token in its query
    string. Origin gets stored in files and logs, so keep only scheme, host,
    port and path.
    """
    parts = urlsplit(url)
    return urlunsplit((parts.scheme, _strip_userinfo(parts.netloc), parts.path, "", ""))


# A query parameter whose NAME contains one of these has its value hidden.
_SECRET_PARAMTER = re.compile(r"token|key|secret|passw|pwd|auth|sig", re.IGNORECASE)


def _public_request_url(url: str) -> str:
    """A request URL that is safe to store, and still works in a browser.

    Unlike ``_public_url`` this KEEPS the query string, since the query is the
    request (site, measurement, dates...). It only removes a username and
    password, and hides the value of any parameter whose name looks like a
    secret. Everything else is left byte for byte as whurl wrote it, so the
    URL can be pasted into a browser and give the same answer. (If a secret
    was hidden, that one parameter has to be put back by hand.)
    """
    parts = urlsplit(url)
    pieces = []
    for piece in parts.query.split("&"):
        name, equals, _value = piece.partition("=")
        if equals and _SECRET_PARAMTER.search(name):
            piece = f"{name}=REDACTED"
        pieces.append(piece)
    query = "&".join(pieces)
    return urlunsplit(
        (parts.scheme, _strip_userinfo(parts.netloc), parts.path, query, parts.fragment)
    )

# Hilltop's wording for an empty range, e.g. "No data from 25-Oct-2026 16:32:10
# to 28-Oct-2026 16:32:10". Seen in a real response; whurl wraps it with a prefix.
_NO_DATA = re.compile(r"\bNo data\b", re.IGNORECASE)

def _request_url_for(client, kwargs: dict) -> str:
    """The URL whurl WOULD have requested, built the same way its client does."""
    request = GetDataRequest(
        base_url=str(client.base_url),
        hts_endpoint=str(client.hts_endpoint),
        **kwargs,
    )
    return request.gen_url()
