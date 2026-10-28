"""Tests for HorizonsProvider.

HOW THESE TESTS WORK
--------------------
The real provider talks to a Hilltop server through whurl's HilltopClient.
We never want tests to hit a server (slow, flaky, data changes), so most tests
swap the real client for a FAKE: a tiny class that has the same ``get_data``
method but returns data we've hard-coded. The provider can't tell the difference.

So each tests follows this pattern:
    1. Build the data the "server" will return (small pandas DataFrame)
    2. Hand it to FakeArchive, and plug that into a provider.
    3. Call the provider method and check the answer.

The data shapes copy what whurl really returns, e.g. one column named after
the measurement (the value) plus a "Quality" column, indexed by timestamp.
"""


from datetime import datetime
from types import SimpleNamespace
from urllib.parse import quote
from typing import Any

import numpy as np
import pandas as pd
import pytest

from hydrobot.orchestration.resolve import ResolveProvider
from hydrobot.providers.horizons import HorizonsProvider, HorizonsProviderConfig
from hydrobot.providers.protocol import DataProvider
from hydrobot.providers.types import DataProviderError

SITE, MEAS = "Manawatu at Teachers College", "Atmospheric Pressure"


# A copy of the provider_params block from a real hydrobot YAML config.
# If the YAML keys and HorizonsProviderConfig ever drift apart, the first
# test below fails.
YAML_PROVIDER_PARAMS = {
    "base_url": "http://example.invalid/",
    "standard_hts_filename": "RawLoggerNet.hts",
    "check_hts_filename": "HydrobotCheckData.hts",
    "archive_base_url": "http://archample.invalid/",
    "archive_standard_hts_filename": "Archive.hts",
    "archive_check_hts_filename": "Archive.hts"
}


def fake_response(df, name=MEAS, ts_type="StdSeries"):
    """Wrap a DataFrame in the same nesting whurl's real response has.

    The provider reaches the data by walking
    ``response.measurements[i].data_source.name`` and
    ``response.measurements[i].data.timeseries``. SimpleNamespace is just a
    quick way to make an object with those attributes, without needing the
    real whurl reponse classes (or a server).

    """
    return SimpleNamespace(
        measurements=[
            SimpleNamespace(
                data_source=SimpleNamespace(name=name, ts_type=ts_type),
                data=SimpleNamespace(timeseries=df),
            )
        ]
    )


class ClosableFake:
    """The part of a real client's lifecycle that matters: closed is final.

    whurl's real client (like the http library its based on) refuses to send
    anything once it's been closed. An earlier version of the provider
    closed its clients after every read, and the fakes did not notice,
    because they would happily keep answering. They now inherit from this,
    so a provider that closes a client too early fails its tests.
    """

    closed = False

    def close(self):
        self.closed = True

    def _check_open(self):
        if self.closed:
            raise RuntimeError("Cannot send a request, as the client has been closed.")


class FakeArchive(ClosableFake):
    """Stand-in for whurl's HilltopClient; pointed at the archive.

    You give it two DataFrames up front: what the archive "contains" as its
    quality series and as its standard series. When the provider calls
    ``get_data``, it hands back the matching one based on the ``ts_type`` the
    provider asked for ("StdQualSeries" or "StdSeries").

    It also records every call it receives in ``self.calls``, so tests can
    check what the provider *asked for*, not just what it returned.

    Like the real client, it refuses requests once closed (see ClosableFake).
    """

    def __init__(self, qual_df, std_df, data_source=MEAS):
        self.qual_df = qual_df
        self.std_df = std_df
        # The data source name the "server" reports (see the bracketed-name test).
        self.data_source = data_source
        self.calls = [] # each get_data call's keyword arguments, in order

    def get_data(self, **kwargs):
        self._check_open()
        self.calls.append(kwargs)
        # Answer with the series type that was asked for, labelled as such.
        ts_type = kwargs["ts_type"]
        df = self.qual_df if ts_type == "StdQualSeries" else self.std_df

        return fake_response(df, name=self.data_source, ts_type=ts_type)


def provider_with(archive):
    """A HorizonsProvider whose archive client is ``archive`` (a fake, or None).

    ``object.__new__`` creates the object WITHOUT running ``__init__``. The
    real ``__init__`` would build real HilltopClients, we skip that and set
    only the one attribute ``last_processed_time`` uses.
    """
    p = object.__new__(HorizonsProvider) # skip __init__: no real clients
    p.archive_client = archive
    return p

def timestamps(*times):
    return pd.DatetimeIndex(times, name="DateTime")

# --- construction and conformance ------------------------------------------------

def test_builds_from_yaml_provider_params():
    # Uses the REAL __init__ (and so real HilltopClients, which don't touch
    # the network until you ask them for data). Proves the config model
    # accepts exactly the keys our YAML files contain.
    p = HorizonsProvider(HorizonsProviderConfig(**YAML_PROVIDER_PARAMS))
    assert p.archive_client is not None


def test_archive_is_optional():
    # A council with no archive can leave the archive_* keys out entirely.
    params = {k: v for k, v in YAML_PROVIDER_PARAMS.items() if "archive" not in k}
    p = HorizonsProvider(HorizonsProviderConfig(**params))
    assert p.archive_client is None


def test_satisfied_what_resolve_needs():
    # resolve() only asks its provider for last_processed_time and
    # get_site_info (it declares that as ResolveProvider). Check the real
    # provider fits, so the narrow type used in orchestration can't drift
    # from the real class
    p = HorizonsProvider(HorizonsProviderConfig(**YAML_PROVIDER_PARAMS))
    assert isinstance(p, ResolveProvider)


def test_implements_every_protocol_method():
    # HorizonsProvider doesn't inherit from DataProvider, so Python won't
    # complain if we forget a method until something calls it. This test
    # does the checking instead: list the Protocol's public methods, and
    # make sure each one is defined on HorizonsProvider itself.
    expected = [
        name
        for name, value in vars(DataProvider).items()
        if callable(value) and not name.startswith("_")
    ]
    missing = [name for name in expected if name not in vars(HorizonsProvider)]
    assert not missing, f"HorizonsProvider is missing: {missing}"


# --- last_processed_time ---------------------------------------------------------


def test_real_archive_example_resumes_at_checkpoint():
    # Taken from a real archive: the last data point is older than a QC 100
    # "missing record" checkpoint at 22 Oct 11:00. Processing got as far as the
    # checkpoint, so that's where we resume.
    qual = pd.DataFrame({MEAS: [100]}, index=timestamps("2025-10-22 11:00:00"))
    std = pd.DataFrame() # nothing in the standard series after the checkpoint
    archive = FakeArchive(qual, std)

    result = provider_with(archive).last_processed_time(SITE, MEAS)

    assert result == pd.Timestamp("2025-10-22 11:00:00")


def test_bracketed_measurement_names_match_in_the_archive_too():
    # Names can be "Item [Data Source]", but the server reports only the data
    # source part. The archive lookup must match on that part, the same as
    # every other read (it once compared the whole string and never matched).
    name = "Water Temperature [Water Temperature (Hobo)]"
    qual = pd.DataFrame({"x": [600]}, index=timestamps("2025-01-01 00:00"))
    archive = FakeArchive(qual, pd.DataFrame(), data_source="Water Temperature (Hobo)")

    result = provider_with(archive).last_processed_time(SITE, name)

    assert result == pd.Timestamp("2025-01-01 00:00")


def test_std_fetch_starts_at_last_quality_entry_and_asks_for_quality():
    # Checks what the provider ASKED the server, via the fake's call log.
    # A GetData with no time range returns only the latest point, so the
    # provider makes two calls:
    #   1. The quality series, no range -> just its latest entry
    #   2. The standard series with quality, starting from that entry's time.
    qual = pd.DataFrame({MEAS: [600]}, index=timestamps("2025-01-01 00:00"))
    arch = FakeArchive(qual, pd.DataFrame())

    provider_with(arch).last_processed_time(SITE, MEAS)

    qual_call, std_call = arch.calls  # exactly two calls, in this order

    assert qual_call["ts_type"] == "StdQualSeries"
    assert "from_datetime" not in qual_call # no range: latest entry only
    assert std_call["ts_type"] == "StdSeries"
    assert std_call["show_quality"] == "Yes"
    assert std_call["from_datetime"] == pd.Timestamp("2025-01-01 00:00")


def test_trailing_unprocessed_chunk_ignored():
    # Three standard points. The first has quality 600 (processed). The last
    # two have quality 0 (copied up to the archive without being processed).
    # We should resume right after the last PROCESSED point, not at the end.
    qual = pd.DataFrame({MEAS: [600]}, index=timestamps("2025-01-01 00:00"))
    std = pd.DataFrame(
        {MEAS: [1.0, 2.0, 3.0], "Quality": [600, 0, 0]},
        index=timestamps("2025-01-01 00:00", "2025-01-01 01:00", "2025-01-01 02:00"),
    )

    assert provider_with(FakeArchive(qual, std)).last_processed_time(
        SITE, MEAS
    ) == pd.Timestamp("2025-01-01 00:00")


def test_never_archived_returns_none():
    # Empty archive: no quality entries, no data. The provider just reports
    # "never processed" (None). Whether that's an error is the caller's call.
    arch = FakeArchive(pd.DataFrame(), pd.DataFrame())

    assert provider_with(arch).last_processed_time(SITE, MEAS) is None


# --- Error handling: each of these should fail with a clear message ----------


def test_missing_archive_config_is_a_clear_error():
    # No arhive configured (archive_client is None): asking for the last
    # processed time can't work, so say why instead of crashing obscurely.
    with pytest.raises(DataProviderError, match="archive"):
        provider_with(None).last_processed_time(SITE, MEAS)


def test_std_without_quality_column_is_a_clear_error():
    # The standard data came back with values but no "Quality" column, e.g.
    # because the request forgot show_quality="Yes". Fail loudly: silently
    # carrying on would make every point look unprocessed.
    qual = pd.DataFrame({MEAS: [600]}, index=timestamps("2025-01-01 00:00"))
    std = pd.DataFrame({MEAS: [1.0]}, index=timestamps("2025-01-01 00:00"))

    with pytest.raises(DataProviderError, match="Quality"):
        provider_with(FakeArchive(qual, std)).last_processed_time(SITE, MEAS)


class DuplicatingArchive(FakeArchive):
    """A fake archive that returns the same measurement TWICE per response.

    Simulates a server answering with duplicate matches, which the provider
    should refuse to guess between.
    """

    def get_data(self, **kwargs):
        response = super().get_data(**kwargs)
        response.measurements.append(response.measurements[0])
        return response

def test_multiple_matching_measurements_is_an_error():
    qual = pd.DataFrame({MEAS: [600]}, index=timestamps("2025-01-01 00:00"))
    archive = DuplicatingArchive(qual, pd.DataFrame())

    with pytest.raises(DataProviderError, match="Multiple"):
        provider_with(archive).last_processed_time(SITE, MEAS)


def test_quality_frame_with_extra_columns_is_an_error():
    # The quality series should be a single column of codes. Two columns means
    # we're not looking at what we think we are, so don't guess which to use.
    qual = pd.DataFrame(
        {"a": [1], "b": [2]}, index=timestamps("2025-01-01 00:00")
    )

    with pytest.raises(DataProviderError, match="single quality"):
        provider_with(FakeArchive(qual, pd.DataFrame())).last_processed_time(SITE, MEAS)


# -----------------------------------------------------------------------------
# get_site_info
#
# whurl returns site info as a list of sites, each with a name and a dict of
# fields. The provider picks the field holding the site code (at Horizons,
# "SecondSynonym") and returns it as a normalised SiteInfo.
# -----------------------------------------------------------------------------


# A real SiteInfo response from the Horizons server (trimmed from ~50 fields).
# Note the field is the XML tag "SecondSynonym": the space in "Second Synonym"
# is only how Hilltop's own screens display it.
SITE_INFO_XML = """<?xml version="1.0" ?>
<HilltopServer>
<Agency>Horizons</Agency>
<Site Name="Manawatu at Teachers College">
<AEP0.01>3678000</AEP0.01>
<AirQNES>false</AirQNES>
<Altitude>21.209</Altitude>
<SecondSynonym>TCO</SecondSynonym>
<ShortName>Hor-0034</ShortName>
<SiteID>340</SiteID>
</Site>
</HilltopServer>"""

class FakeSiteClient:
    """Stands in for HilltopClient for site-info requests only."""

    def __init__(self, sites):
        # sites: a list of (name, {field: value}) pairs the "server" knows.
        self.sites = sites
        self.calls = []

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def get_site_info(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(
            site=[SimpleNamespace(name=n, info=i) for n, i in self.sites]
        )


def provider_with_sites(sites, field="SecondSynonym"):
    # Typed as Any because we deliberately put a fake where a real
    # HilltopClient belongs, and the type checker will complain.
    p: Any = object.__new__(HorizonsProvider)  # skip __init__: no real clients
    p.client = FakeSiteClient(sites)
    p.site_code_field = field
    return p


def test_site_code_read_from_the_configured_field():
    p = provider_with_sites([(SITE, {"SecondSynonym": "TCO", "Other": "x"})])
    info = p.get_site_info(SITE)
    assert info.code == "TCO"
    assert info.metadata["Other"] == "x"  # the rest is kept, unprocessed
    assert p.client.calls == [{"site": SITE}]


def test_site_code_field_is_configurable():
    # Another council (or a renamed field) just changes the setting.
    p = provider_with_sites([(SITE, {"Code": "TCO"})], field="Code")
    assert p.get_site_info(SITE).code == "TCO"



def test_missing_code_field_lists_what_is_available():
    # The likeliest mistake is the wrong field name, so the error lists the
    # fields that DO exist.
    p = provider_with_sites([(SITE, {"Synonym": "TCO"})])
    with pytest.raises(DataProviderError, match="Synonym"):
        p.get_site_info(SITE)


def test_blank_code_is_an_error():
    # A field that exists but is empty is no use as a file-name component.
    p = provider_with_sites([(SITE, {"SecondSynonym": "  "})])
    with pytest.raises(DataProviderError, match="no usable"):
        p.get_site_info(SITE)


def test_site_not_found_is_an_error():
    # The server returned some other site (or none): not what we asked about.
    p = provider_with_sites([("Some Other Site", {"SecondSynonym": "XXX"})])
    with pytest.raises(DataProviderError, match="exactly one"):
        p.get_site_info(SITE)


def test_real_site_info_xml_through_whurls_parser():
    # End to end through whurl's REAL parser (only the network is faked): a
    # genuine Horizons response goes in, and the provider must find the code.
    # This is what guards against the field name drifting from reality.
    from whurl.schemas.responses.site_info import SiteInfoResponse

    parsed = SiteInfoResponse.from_xml(SITE_INFO_XML)

    class ParsedClient:
        """Hands back the already-parsed response, like HilltopClient would."""

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def get_site_info(self, **kwargs):
            return parsed

    p: Any = object.__new__(HorizonsProvider)  # skip __init__: no real clients
    p.client = ParsedClient()
    # Use the DEFAULT field name from the config, not a hand-typed one, so the
    # test fails if the default ever stops matching real responses.
    p.site_code_field = HorizonsProviderConfig(**YAML_PROVIDER_PARAMS).site_code_field

    info = p.get_site_info("Manawatu at Teachers College")

    assert info.code == "TCO"
    assert info.metadata["ShortName"] == "Hor-0034" # other fields kept

# -----------------------------------------------------------------------------
# get_standard
#
# The provider asks Hilltop for a standard series and returns it with a tidy
# metadata dict. These tests pin down the three outcomes (data / empty / wrong
# name) and the translation from Hilltop's vocabulary to hydrobot's.
# -----------------------------------------------------------------------------

START, END = pd.Timestamp("2025-01-01"), pd.Timestamp("2025-01-02")


def std_measurement(data_source="Atmospheric Pressure", ts_type="StdSeries",
                    divisor=None, df=None):
    """One <Measurement> as whurl would parse it, with a single item"""
    if df is None:
        df = pd.DataFrame(
            {"Atmospheric Pressure": [1002.66]}, index=timestamps("2025-01-01 00:00")
        )

    return SimpleNamespace(
        data_source=SimpleNamespace(
            name=data_source,
            ts_type=ts_type,
            item_info=[
                SimpleNamespace(
                    item_name="Atmospheric Pressure",
                    item_format="F",
                    divisor=divisor,
                    units="hPa",
                    format="#.#",
                )
            ],
        ),
        data=SimpleNamespace(timeseries=df),
    )


# The pretend "now" (current datetime) for every origin recorded in these tests.
FIXED_NOW = datetime(2026, 10, 19, 9, 30)



class FakeStandardClient:
    """Stands in for HilltopClient; returns the measurements you give it.

    ``base_url`` and ``hts_endpoint`` are what the real client exposes; the
    provider records them in each read's origin.

    Like the real client, it attaches the request it "made" to the response
    (``response.request.gen_url()``), which is where the provider gets the
    request URL for the origin. ``last_url`` is the URL it generated for the
    most recent call, so tests can compare against it.
    """

    base_url = "http://example.invalid/hilltop"
    hts_endpoint = "RawLoggerNet.hts"

    def __init__(self, measurements):
        self.measurements=measurements
        self.calls = []
        self.last_url = None

    def _url_for(self, kwargs):
        # The same shape whurl builds: percent-encoded, in a fixed order.
        return (
            f"{self.base_url}/{self.hts_endpoint}?Service=Hilltop&Request=GetData"
            f"&Site={quote(kwargs['site'])}&Measurement={quote(kwargs['measurement'])}"
            f"&TSType={kwargs['ts_type']}"
        )

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def get_data(self, **kwargs):
        self.calls.append(kwargs)
        self.last_url = self._url_for(kwargs)
        return SimpleNamespace(
            measurements=self.measurements,
            request=SimpleNamespace(gen_url=lambda: self.last_url),
        )


def provider_returning(measurements):
    p: Any = object.__new__(HorizonsProvider)  # skip __init__: no real clients
    p.client = FakeStandardClient(measurements)
    p._clock = lambda: FIXED_NOW  # a fixed clock, so origins are predictable
    return p


def test_standard_data_and_metadata_returned():
    # The metadata used hydrobot's names. In particular Hilltop's "format"
    # becomes "number_format", the key the Processor already users.
    p = provider_returning([std_measurement()])
    result = p.get_standard(SITE, MEAS, START, END)
    assert result.data.iloc[0, 0] == 1002.66
    without_origin = {k: v for k, v in result.metadata.items() if k != "origin"}
    assert without_origin == {
        "item_name": "Atmospheric Pressure",
        "item_format": "F",
        "divisor": 1,
        "units": "hPa",
        "number_format": "#.#",
    }


def test_standard_request_uses_stdseries_and_the_given_dates():
    # Check what the provider ASKED for, via the fake's call log.
    p = provider_returning([std_measurement()])
    p.get_standard(SITE, MEAS, START, END)
    assert p.client.calls == [
        {
            "site": SITE,
            "measurement": MEAS,
            "from_datetime": START,
            "to_datetime": END,
            "ts_type": "StdSeries",
        }
    ]


def test_missing_divisor_means_one_and_a_real_divisor_is_passed_through():
    # Hilltop omits the divisor when it's 1 (we see None). A real divisor is
    # reported for information only: whurl has already applied it to the data.
    none = provider_returning([std_measurement(divisor=None)])
    ten = provider_returning([std_measurement(divisor=10)])
    assert none.get_standard(SITE, MEAS, START, END).metadata["divisor"] == 1
    assert ten.get_standard(SITE, MEAS, START, END).metadata["divisor"] == 10


def test_bracketed_names_match_on_the_data_source_part():
    # Hilltop names can be "Item [Data Source]". The data source is the
    # bracketed part, so that's what has to match what the server returns.
    name = "Water Temperature [Water Temperature (Hobo)]"
    p = provider_returning([std_measurement(data_source="Water Temperature (Hobo)")])
    assert not p.get_standard(SITE, name, START, END).data.empty


def test_no_data_in_range_is_empty_not_an_error():
    # A quiet period returns no measurements at all. That's normal, so the
    # provider hands back empty data and leaves the reporting to the caller.
    for nothing in ([], None):
        result = provider_returning(nothing).get_standard(SITE, MEAS, START, END)
        assert result.data.empty
        assert result.metadata.keys() == {"origin"}


def test_wrong_measurement_name_is_an_error_listing_the_alternatives():
    # Data came back, but none of it is what we asked for: almost certainly a
    # wrong name, so say what the server DID have.
    p = provider_returning([std_measurement(data_source="Something Else")])
    with pytest.raises(DataProviderError, match="Something Else"):
        p.get_standard(SITE, MEAS, START, END)


def test_other_series_types_with_the_same_name_are_ignored():
    # A check series called the same thing must not be mistaken for the
    # standard series. With only that, it's the "not found" case.
    p = provider_returning([std_measurement(ts_type="CheckSeries")])
    with pytest.raises(DataProviderError, match="not found"):
        p.get_standard(SITE, MEAS, START, END)


def test_duplicate_standard_series_is_an_error():
    # Two matching series: we can't know which is right, so don't guess.
    p = provider_returning([std_measurement(), std_measurement()])
    with pytest.raises(DataProviderError, match="Multiple"):
        p.get_standard(SITE, MEAS, START, END)


# ---------------------------------------------------------------------------
# get_quality
#
# The quality series is one column of integer quality codes. Having none is
# NORMAL (nothing processed yet), so "not found" is empty data, not an error.
# ---------------------------------------------------------------------------


def qual_measurement(data_source="Atmospheric Pressure", ts_type="StdQualSeries",
                     codes=(600, 100)):
    """One quality <Measurement> as whurl parses it (values are floats)."""
    df = pd.DataFrame(
        {"Atmospheric Pressure": [float(c) for c in codes]},
        index=timestamps("2025-01-01 00:00", "2025-01-01 06:00")[: len(codes)],
    )
    return SimpleNamespace(
        data_source=SimpleNamespace(name=data_source, ts_type=ts_type, item_info=[]),
        data=SimpleNamespace(timeseries=df),
    )


def test_quality_codes_come_back_as_integers():
    # whurl hands quality over as floats (600.0); the contract is whole numbers.
    p = provider_returning([qual_measurement()])
    result = p.get_quality(SITE, MEAS, START, END)
    assert list(result.data.iloc[:, 0]) == [600, 100]
    assert result.data.iloc[:, 0].dtype.kind == "i"


def test_quality_request_uses_stdqualseries():
    p = provider_returning([qual_measurement()])
    p.get_quality(SITE, MEAS, START, END)
    assert p.client.calls[0]["ts_type"] == "StdQualSeries"
    assert p.client.calls[0]["from_datetime"] == START


def test_no_quality_series_is_empty_not_an_error():
    # Nothing returned at all, or only a series for some other data source.
    # Both just mean "no quality yet".
    for returned in ([], None, [qual_measurement(data_source="Something Else")]):
        result = provider_returning(returned).get_quality(SITE, MEAS, START, END)
        assert result.data.empty


def test_quality_ignores_other_series_types():
    # A standard series of the same name is not a quality series.
    p = provider_returning([qual_measurement(ts_type="StdSeries")])
    assert p.get_quality(SITE, MEAS, START, END).data.empty


def test_duplicate_quality_series_is_an_error():
    p = provider_returning([qual_measurement(), qual_measurement()])
    with pytest.raises(DataProviderError, match="Multiple StdQualSeries"):
        p.get_quality(SITE, MEAS, START, END)


# ---------------------------------------------------------------------------
# get_check
#
# Check data has several items (the check value, "Recorder Time", "Comment").
# whurl names the columns, types them and applies divisors; the provider
# passes that frame through with the item metadata in COLUMN order.
# ---------------------------------------------------------------------------

# A real check response from the Horizons server. Look closely at the
# ItemInfo blocks: they're listed in the order 1, 3, 2 (Comment before
# Recorder Time), though the data columns come out in item-number order.
CHECK_XML = """<?xml version="1.0" ?>
<Hilltop>
<Agency>Horizons</Agency>
<Measurement SiteName="Manawatu at Teachers College">
<DataSource Name="Atmospheric Pressure" NumItems="3">
<TSType>CheckSeries</TSType>
<DataType>SimpleTimeSeries</DataType>
<Interpolation>Discrete</Interpolation>
<ItemFormat>45</ItemFormat>
<ItemInfo ItemNumber="1"><ItemName>Check Pressure</ItemName><ItemFormat>F</ItemFormat><Divisor>1</Divisor><Units>hPa</Units><Format>####.#</Format></ItemInfo>
<ItemInfo ItemNumber="3"><ItemName>Comment</ItemName><ItemFormat>S</ItemFormat><Divisor>1</Divisor><Units></Units><Format>###</Format></ItemInfo>
<ItemInfo ItemNumber="2"><ItemName>Recorder Time</ItemName><ItemFormat>D</ItemFormat><Divisor>1</Divisor><Units></Units><Format>#.##</Format></ItemInfo>
</DataSource>
<Data DateFormat="Calendar" NumItems="3">
<E><T>2025-10-22T11:09:00</T><I1>1009</I1><I2>560418892</I2><I3></I3></E>
</Data>
</Measurement>
</Hilltop>"""


def parsed_check_response():
    """CHECK_XML through whurl's REAL parser, shaped as the provider expects.

    Older whurl builds name the list ``measurement`` rather than
    ``measurements``; accept either so the test runs against both.
    """
    from whurl.schemas.responses.get_data import GetDataResponse

    return GetDataResponse.from_xml(CHECK_XML).measurements


class FakeCheckClient(FakeStandardClient):
    """Same fake, used as the CHECK client (a different HTS from standard)."""

    hts_endpoint = "HydrobotCheckData.hts"


def provider_with_check(measurements):
    p: Any = object.__new__(HorizonsProvider)  # skip __init__: no real clients
    p.check_client = FakeCheckClient(measurements)
    p._clock = lambda: FIXED_NOW  # a fixed clock, so origins are predictable
    return p


CHECK_NAME = "Check Pressure [Atmospheric Pressure]"


def test_check_data_is_passed_through_by_item_name():
    # Real response, real parser: columns are named by item and already typed
    # (float, datetime, text) with no further work needed by the caller.
    p = provider_with_check(parsed_check_response())
    result = p.get_check(SITE, CHECK_NAME, START, END)
    assert list(result.data.columns) == ["Check Pressure", "Recorder Time", "Comment"]
    assert result.data["Check Pressure"].iloc[0] == 1009.0
    assert pd.api.types.is_datetime64_any_dtype(result.data["Recorder Time"])


def test_check_metadata_is_in_column_order_not_xml_order():
    # The response lists ItemInfo as 1, 3, 2 but the columns are 1, 2, 3.
    # Metadata must follow the COLUMNS, otherwise anything pairing the two by
    # position (as the old Processor did) formats the wrong columns.
    p = provider_with_check(parsed_check_response())
    meta = p.get_check(SITE, CHECK_NAME, START, END).metadata
    assert [i["item_name"] for i in meta["items"]] == [
        "Check Pressure", "Recorder Time", "Comment",
    ]
    assert [i["item_format"] for i in meta["items"]] == ["F", "D", "S"]
    assert meta["items"][0] == {
        "item_name": "Check Pressure", "item_format": "F", "divisor": 1,
        "units": "hPa", "number_format": "####.#",
    }
    assert meta["item_format"] == "45"


def test_check_request_goes_to_the_check_hts_with_checkseries():
    p = provider_with_check(parsed_check_response())
    p.get_check(SITE, CHECK_NAME, START, END)
    call = p.check_client.calls[0]
    assert call["ts_type"] == "CheckSeries"
    assert call["measurement"] == CHECK_NAME


def test_no_check_data_is_empty_not_an_error():
    # Nothing in range, or only some other data source: reported by the
    # caller, never raised here. There is no fallback to another name.
    for returned in ([], None):
        assert provider_with_check(returned).get_check(SITE, CHECK_NAME, START, END).data.empty
    other = parsed_check_response()
    other[0].data_source.name = "Something Else"
    assert provider_with_check(other).get_check(SITE, CHECK_NAME, START, END).data.empty


def test_duplicate_check_series_is_an_error():
    twice = parsed_check_response() * 2
    with pytest.raises(DataProviderError, match="Multiple CheckSeries"):
        provider_with_check(twice).get_check(SITE, CHECK_NAME, START, END)


# -----------------------------------------------------------------------------
# Origin: where each read's data came from
#
# Every data read records ``metadata["origin"]``: which provider, which server
# and HTS, what was asked for, and when. It's the first step towards being able
# to answer "where did this value come from?" in a drilldown plot.
# -----------------------------------------------------------------------------


def test_standard_origin_describes_the_read():
    p = provider_returning([std_measurement()])
    origin = p.get_standard(SITE, MEAS, START, END).metadata["origin"]
    assert origin == {
        "provider": "horizons-hilltop",
        "source_tag": "HTP",
        "base_url": "http://example.invalid/hilltop",
        "hts": "RawLoggerNet.hts",
        # Open this in a browser to reproduce the read.
        "request_url": (
            "http://example.invalid/hilltop/RawLoggerNet.hts?Service=Hilltop"
            "&Request=GetData&Site=Manawatu%20at%20Teachers%20College"
            "&Measurement=Atmospheric%20Pressure&TSType=StdSeries"
        ),
        "site": SITE,
        "measurement": MEAS,
        "ts_type": "StdSeries",
        "from_date": START,  # the range REQUESTED, not what came back
        "to_date": END,
        "retrieved_at": FIXED_NOW,
    }


def test_quality_origin_uses_the_standard_hts_and_stdqualseries():
    # Quality lives beside the standard data, so it comes from the same HTS.
    p = provider_returning([qual_measurement()])
    origin = p.get_quality(SITE, MEAS, START, END).metadata["origin"]
    assert origin["ts_type"] == "StdQualSeries"
    assert origin["hts"] == "RawLoggerNet.hts"


def test_check_origin_uses_the_check_hts():
    # Check data comes from a DIFFERENT HTS, and the origin must say so.
    p = provider_with_check(parsed_check_response())
    origin = p.get_check(SITE, CHECK_NAME, START, END).metadata["origin"]
    assert origin["ts_type"] == "CheckSeries"
    assert origin["hts"] == "HydrobotCheckData.hts"
    assert origin["source_tag"] == "HTP"


def test_origin_is_recorded_even_when_nothing_was_found():
    # Quality and check data reads that find nothing still say what was asked
    # and where. (The standard read is covered with its own empty test above.)
    quality = provider_returning([]).get_quality(SITE, MEAS, START, END)
    check = provider_with_check([]).get_check(SITE, CHECK_NAME, START, END)
    assert quality.data.empty and quality.metadata["origin"]["measurement"] == MEAS
    assert check.data.empty and check.metadata["origin"]["measurement"] == CHECK_NAME

def test_origin_url_has_credentials_and_query_removed():
    # A base URL might carry a password or a token. Origin ends up in files
    # and logs, so only scheme, host, port and path are kept.
    p = provider_returning([std_measurement()])
    p.client.base_url = "https://analyst:speven2@hilltop.example.nz:8443/data?token=abc123"
    origin = p.get_standard(SITE, MEAS, START, END).metadata["origin"]
    assert origin["base_url"] == "https://hilltop.example.nz:8443/data"
    assert "speven2" not in str(origin) and "abc123" not in str(origin)


# -----------------------------------------------------------------------------
# The request URL in the origin
#
# whurl attaches the request it built to each response, so the provider can
# record the exact URL. Pasted into a browser it reproduces the read, which is
# the quickest way to debug "why is this data wrong?". Because it's stored in
# files and logs, secrets must be removed first, but the query stays, since the
# query IS the request.
# -----------------------------------------------------------------------------

# The URL in the origin must come from the request that was really made, not
# be rebuilt separately from somewhere else. The fake client remembers the URL it
# generated for its most recent call (``last_url``), so each test makes one
# read and checks the origin holds exactly that URL.


def test_standard_read_records_the_url_it_requested():
    p = provider_returning([std_measurement()])
    origin = p.get_standard(SITE, MEAS, START, END).metadata["origin"]
    assert origin["request_url"] == p.client.last_url


def test_quality_read_records_the_url_it_requested():
    p = provider_returning([qual_measurement()])
    origin = p.get_quality(SITE, MEAS, START, END).metadata["origin"]
    assert origin["request_url"] == p.client.last_url


def test_check_records_the_url_it_requested():
    # Check data goes through the CHECK client, so that's the one to ask.
    p = provider_with_check(parsed_check_response())
    origin = p.get_check(SITE, CHECK_NAME, START, END).metadata["origin"]
    assert origin["request_url"] == p.check_client.last_url


def test_request_url_is_kept_even_when_nothing_was_found():
    # An empty result is exactly when you most want to re-run the request in a
    # browser and see what the server says.
    result = provider_returning([]).get_standard(SITE, MEAS, START, END)
    assert result.metadata["origin"]["request_url"].startswith("http://example.invalid/")


def test_request_url_has_credentials_removed_but_keeps_the_query_untouched():
    # Credentials in the address come out. Everything else, including the
    # percent-coding (e.g. %20) stays byte-for-byte so the URL still works in a browser.
    p = provider_returning([std_measurement()])
    p.client.base_url = "http://analyst:speven2@example.invalid/hilltop"
    url = p.get_standard(SITE, MEAS, START, END).metadata["origin"]["request_url"]
    assert "speven2" not in url and "analyst" not in url
    assert url == (
        "http://example.invalid/hilltop/RawLoggerNet.hts?Service=Hilltop"
        "&Request=GetData&Site=Manawatu%20at%20Teachers%20College"
        "&Measurement=Atmospheric%20Pressure&TSType=StdSeries"
    )


def test_request_url_hides_secret_looking_parameters_only():
    # A parameter whose NAME looks like a secret has its value replaced.
    # The rest of the query is left exactly as it was.
    from hydrobot.providers.horizons import _public_request_url

    url = "https://h.example.nz/a.hts?Service=Hilltop&ApiKey=abc123&Site=Lake%20A&token=xyz&Flag"
    assert _public_request_url(url) == (
        "https://h.example.nz/a.hts?Service=Hilltop&ApiKey=REDACTED&Site=Lake%20A&token=REDACTED&Flag"
    )
