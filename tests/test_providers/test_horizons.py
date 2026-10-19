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


from types import SimpleNamespace
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


def fake_response(df, name=MEAS):
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
                data_source=SimpleNamespace(name=name),
                data=SimpleNamespace(timeseries=df),
            )
        ]
    )


class FakeArchive:
    """Stand-in for whurl's HilltopClient; pointed at the archive.

    You give it two DataFrames up front: what the archive "contains" as its
    quality series and as its standard series. When the provider calls
    ``get_data``, it hands back the matching one based on the ``ts_type`` the
    provider asked for ("StdQualSeries" or "StdSeries").

    It also records every call it receives in ``self.calls``, so tests can
    check what the provider *asked for*, not just what it returned.

    ``__enter__`` / ``__exit__`` exist because the provider uses the client in
    a ``with`` block (the real client opens and closes a connection there).
    The fake has nothing to open or close, so they do nothing.
    """

    def __init__(self, qual_df, std_df):
        self.qual_df = qual_df
        self.std_df = std_df
        self.calls = [] # each get_data call's keyword arguments, in order

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def get_data(self, **kwargs):
        self.calls.append(kwargs)
        if kwargs["ts_type"] == "StdQualSeries":
            return fake_response(self.qual_df)
        return fake_response(self.std_df)


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
