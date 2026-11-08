"""Shared test helpers for anything that sits on top of a provider.

WHY THIS EXISTS
---------------
The Processor asks a *provider* for data. In tests we never want a server, so
we hand it a FakeProvider: an object with the same methods as the real thing,
returning data we chose, and remembering what it was asked.

Two rules, both learned the hard way (see ARCHITECTURE.md, "Testing approach"):

1.  The fake must be AS AWKWARD AS THE REAL PROVIDER. The first live runs
    found bugs that every test missed, because the fakes were kinder than the
    real thing. So:

    *   the data is built by running XML through whurl's REAL parser, so its
        shape (column name, index name, dtypes, NaN for blanks) cannot drift
        from what the provider really returns;
    *   an empty read looks exactly like the provider's: a DataFrame with no
        columns at all, and metadata holding only ``origin``;
    *   a provider that has been closed refuses further reads. The Processor
        does not own the provider (the orchestrator does) and must never
        close it.

2.  A method nobody has asked for yet is NOT silently stubbed. It raises, so a
    Processor that starts calling it unexpectedly fails loudly.
"""

from datetime import datetime, timedelta

import pandas as pd
from whurl.schemas.responses import GetDataResponse

from hydrobot.providers.types import (
    CheckData,
    DataProviderError,
    QualityData,
    SiteInfo,
    StandardData,
)

SITE = "Manawatu at Teachers College"
MEASUREMENT = "Atmospheric Pressure"

# A real Hilltop response, cut down. {entries} is filled with one <E> per point.
# Dates are the "Calendar" kind (whurl converts them to datetimes for us).
_GET_DATA_XML = """<?xml version="1.0" ?>
<Hilltop>
    <Agency>Test Council</Agency>
    <Measurement SiteName="{site}">
        <DataSource Name="{measurement}" NumItems="1">
            <TSType>StdSeries</TSType>
            <DataType>SimpleTimeSeries</DataType>
            <Interpolation>Instant</Interpolation>
            <ItemInfo ItemNumber="1">
                <ItemName>{measurement}</ItemName>
                <ItemFormat>F</ItemFormat>
                <Divisor>{divisor}</Divisor>
                <Units>hPa</Units>
                <Format>####.#</Format>
            </ItemInfo>
        </DataSource>
        <Data DateFormat="Calendar" NumItems="1">
{entries}
        </Data>
    </Measurement>
</Hilltop>
"""


def make_origin(**overrides) -> dict:
    """An ``Origin`` as the real provider records it (see providers/types.py)."""
    origin = {
        "provider": "fake",
        "source_tag": "FAK",
        "base_url": "http://example.invalid",
        "hts": "RawLoggerNet.hts",
        "site": SITE,
        "measurement": MEASUREMENT,
        "ts_type": "StdSeries",
        "from_date": datetime(2025, 1, 1, 0, 0),
        "to_date": datetime(2025, 1, 1, 1, 0),
        "retrieved_at": datetime(2026, 1, 1, 12, 0),
        "request_url": "http://example.invalid/RawLoggerNet.hts?Service=Hilltop",
    }
    origin.update(overrides)
    return origin

def make_xml(
    values: list[float | None],
    *,
    start: str = "2025-01-01 00:00",
    step_minutes: int = 5,
    positions: list[int] | None = None,
    divisor: int = 1,
    measurement: str = MEASUREMENT,
) -> str:
    """Build the XML a Hilltop server would send for a standard series.

    ``values`` are the readings, one every ``step_minutes`` from ``start``.
    ``None`` is a blank value, which whurl turns into NaN.

    ``positions`` lets a test leave gaps: it gives the slot number of each
    value (default 0, 1, 2, ...), so ``values=[1, 2, 3]`` with
    ``positions=[0, 1, 3]`` has no reading in slot 2.

    ``values`` are the readings as written in the XML. If ``divisor`` is not 1,
    whurl divides them by it while parsing (so ``50.0`` with divisor 10 comes
    out as ``5.0``), exactly as it does for the real provider.
    """
    if positions is None:
        positions = list(range(len(values)))
    first = datetime.fromisoformat(start)

    entries = ""
    for position, value in zip(positions, values, strict=True):
        when = (first + timedelta(minutes=step_minutes * position)).strftime(
            "%Y-%m-%dT%H:%M:%S"
        )
        text = "" if value is None else repr(value)
        entries += f"           <E><T>{when}</T><I1>{text}</I1></E>\n"

    return _GET_DATA_XML.format(
        site=SITE, measurement=measurement, divisor=divisor, entries=entries
    )

def make_standard(
    values: list[float | None],
    *,
    origin: dict | None = None,
    **xml_options,
) -> StandardData:
    """Build a ``StandardData`` the way the real provider would return it.

    The readings are desribed exactly as ``make_xml`` (which takes the
    same options), then run through whurl's real parser. The metadata has the
    same keys the real provider builds in ``get_standard``; the divisor in it
    is for information only.
    """
    xml = make_xml(values, **xml_options)
    response = GetDataResponse.from_xml(xml)
    measurement_ = response.measurements[0]
    item = measurement_.data_source.item_info[0]

    metadata = {
        "item_name": item.item_name,
        "item_format": item.item_format,
        "divisor": 1 if item.divisor is None else item.divisor,
        "units": item.units,
        "number_format": item.format,
        "origin": (
            origin
            if origin is not None
            else make_origin(measurement=xml_options.get("measurement", MEASUREMENT))
        ),
    }
    return StandardData(data=measurement_.data.timeseries, metadata=metadata)


def empty_standard(origin: dict | None = None) -> StandardData:
    """What the real provider returns when the range holds no data.

    Note what is NOT here: no columns, no index, and none of the item
    metadata. Only the origin survives, because "we asked and got nothing" is
    worth knowing.
    """
    return StandardData(
        data=pd.DataFrame(),
        metadata={"origin": origin if origin is not None else make_origin()}
    )


class FakeProvider:
    """A DataProvider with canned answers that records every call.

    ``calls`` holds one tuple per call, e.g.
    ``("get_standard", site, measurement, from_date, to_date)``, so a test can
    check what was ASKED, not only what came back.
    """

    def __init__(
        self,
        *,
        standard: StandardData | None = None,
        standard_error: Exception | None = None,
    ):
        self.standard = standard
        self.standard_error = standard_error
        self.calls: list[tuple] = []
        self.closed = False

    # --- lifecycle: owned by whoever built the provider, never the Processor -

    def close(self):
        """Close the provider. After this, reads fail, as with the real one."""
        self.closed = True

    def __enter__(self):
        """Return the provider, so it can be used in a ``with`` block."""
        return self

    def __exit__(self, *exc):
        """Close the provider on leaving the ``with`` block."""
        self.close()

    def _check_open(self):
        if self.closed:
            raise DataProviderError("provider is closed")

    # --- the questions a Processor can ask ---

    def get_standard(self, site, measurement, from_date, to_date) -> StandardData:
        """Return the canned standard data, recording the question."""
        self._check_open()
        self.calls.append(("get_standard", site, measurement, from_date, to_date))
        if self.standard_error is not None:
            raise self.standard_error
        if self.standard is None:
            raise AssertionError("this test gave the FakeProvider no standard data")
        return self.standard

    def get_quality(self, site, measurement, from_date, to_date) -> QualityData:
        """Fail loudly: the Processor does not read quality yet."""
        raise NotImplementedError("the Processor does not read check data yet")

    def last_processed_time(self, site, measurement) -> datetime | None:
        """Fail loudly: only resolve() asks this, not the Processor."""
        raise NotImplementedError("only resolve() asks this, not the Processor")

    def get_site_info(self, site) -> SiteInfo:
        """Fail loudly: only resolve() asks this, not the Processor."""
        raise NotImplementedError("only resolve() asks this, not the Processor")


def make_run_config(**overrides) -> dict:
    """A complete run config, as ``resolve()`` would produce it.

    Only the keys the Processor reads. Real run configs carry many more (the
    Processor ignores them), and overrides can add or replace any key.
    """
    config = {
        "site": SITE,
        "standard_measurement_name": MEASUREMENT,
        "data_family": "atmospheric_pressure",
        "from_date": "2025-01-01 00:00",
        "to_date": "2025-01-01 01:00",
    }
    config.update(overrides)
    return config
