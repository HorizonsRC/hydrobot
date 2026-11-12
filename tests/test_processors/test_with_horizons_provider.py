"""The Processor on top of the REAL HorizonsProvider.

HOW THESE TESTS WORK
--------------------
Everything else in this folder uses a FakeProvider. That is only worth
trusting if the fake hands over the same thing as the real provider does. These
tests close that loop. They use the real ``HorizonsProvider`` and fake only
the HTTP client underneath it, and the fake client returns responses that are:

*   parsed by whurl's real XML parser (so the data has the real shapes), and
*   carrying a real whurl ``GetDataRequest`` (so the URLs are the real ones).

So the whole chain, from a Hilltop XML document to the Processor's frame, is
real except for the network.
"""
from hydrobot.data_structure import Data
from pandas.tests.util.test_deprecate_nonkeyword_arguments import i

from datetime import datetime

import pandas as pd
import pytest
from whurl.exceptions import HilltopResponseError
from whurl.schemas.requests import GetDataRequest
from whurl.schemas.responses import GetDataResponse

from hydrobot.processors.processor import Processor
from hydrobot.providers.horizons import HorizonsProvider, HorizonsProviderConfig
from hydrobot.providers.types import DataProviderError
from tests.fake_provider import (
    MEASUREMENT,
    SITE,
    make_run_config,
    make_standard,
    make_xml,
)

BASE_URL = "http://example.invalid"
HTS = "RawLoggerNet.hts"
FROM, TO = datetime(2025, 1, 1, 0, 0), datetime(2025, 1, 1, 1, 0)


class FakeHilltopClient:
    """Stands in for whurl's HilltopClient, answering with real whurl objects.

    Give it the XML the "server" should send, or an exception for it to raise
    (the way the real client does for a Hilltop error document).
    """

    base_url = BASE_URL
    hts_endpoint = HTS

    def __init__(self, xml=None, error=None):
        self.xml = xml
        self.error = error
        self.calls = []
        self.closed = False

    def close(self):
        """Close the client. After this, requests fail, as with the real one."""
        self.closed = True

    def get_data(self, **kwargs):
        """Answer as whurl's client would: a parsed response, or an error."""
        if self.closed:
            raise RuntimeError("Cannot send a request, as the client has been closed.")
        self.calls.append(kwargs)
        if self.error is not None:
            raise self.error
        response = GetDataResponse.from_xml(self.xml)
        # The real client attaches the request it built to every response.
        response.request = GetDataRequest(
            base_url=self.base_url, hts_endpoint=self.hts_endpoint, **kwargs
        )
        return response


def provider_with(client) -> HorizonsProvider:
    """A real HorizonsProvider whose standard client is ``client``."""
    provider = HorizonsProvider(
        HorizonsProviderConfig(
            base_url=BASE_URL,
            standard_hts_filename=HTS,
            check_hts_filename="HydrobotCheckData.hts",
        )
    )
    provider.client.close()  # the real one is not needed
    provider.client = client
    return provider


# The three things the server says when "there is nothing", copied from live
# responses (9 November 2026). They are different things, and the provider must
# tell them apart: only the first is a quiet period.
NO_DATA_ERROR = HilltopResponseError(
    "Response error: Hilltop GetData error: "
    "No data from 9-Nov-2026 08:00:00 to 9-Nov-2026 09:00:00"
)
NO_DATA_SOURCE_ERROR = HilltopResponseError(
    "Response error: Hilltop GetData error: "
    "No Data Source for Atmospheric Pressurk at this site."
)
NO_SITE_ERROR = HilltopResponseError(
    "Response error: Hilltop GetData error: "
    "No data for site Manawatu at Keachers Bollege"
)


class TestTheFakeMatchesTheRealProvider:
    """If these fail, every other test in this folder is testing a fiction."""

    @pytest.fixture()
    def both(self):
        """The same readings, from the real provider and from the fake data."""
        kwargs = {"positions": [0, 1, 3], "divisor": 10}
        values = [50.0, None, 70.0]
        client = FakeHilltopClient(xml=make_xml(values, **kwargs))
        real = provider_with(client).get_standard(SITE, MEASUREMENT, FROM, TO)
        return real, make_standard(values, **kwargs)

    def test_the_data_is_identical(self, both):
        """The data is identical."""
        real, fake = both

        pd.testing.assert_frame_equal(real.data, fake.data)

    def test_the_metadata_has_the_same_keys(self, both):
        """The metadata has the same keys."""
        real, fake = both

        assert set(real.metadata) == set(fake.metadata)
        assert set(real.metadata["origin"]) == set(fake.metadata["origin"])

    def test_the_item_metadata_is_identical(self, both):
        """The item metadata is identical."""
        real, fake = both

        for key in ("item_name", "item_format", "divisor", "units", "number_format"):
            assert real.metadata[key] == fake.metadata[key], key

    def test_an_empty_read_looks_the_same(self):
        """An empty read looks the same."""
        from tests.fake_provider import empty_standard

        real = provider_with(FakeHilltopClient(error=NO_DATA_ERROR)).get_standard(
            SITE, MEASUREMENT, FROM, TO
        )
        fake = empty_standard()

        assert real.data.shape == fake.data.shape == (0, 0)
        assert set(real.metadata) == set(fake.metadata) == {"origin"}


class TestLoadingThroughTheRealProvider:
    """Loading through the real provider."""

    def build(self, client):
        """Return ``(processor, client)`` for a Processor on the real provider."""
        return Processor(make_run_config(), provider_with(client)), client

    def test_the_data_arrives_in_the_frame(self):
        """The data arrives in the frame."""
        xml = make_xml([1000.0, 1001.5, 1002.0])
        processor, _ = self.build(FakeHilltopClient(xml=xml))

        processor.load_data()

        assert list(processor.standard_data["Raw"]) == [1000.0, 1001.5, 1002.0]
        assert processor.standard_data.index.name == "Time"

    def test_the_client_is_asked_the_right_question(self):
        """The client is asked the right question."""
        processor, client = self.build(FakeHilltopClient(xml=make_xml([1.0, 2.0, 3.0])))

        processor.load_data()

        (call,) = client.calls
        assert call["site"] == SITE
        assert call["measurement"] == MEASUREMENT
        assert call["ts_type"] == "StdSeries"
        assert call["from_datetime"] == FROM
        assert call["to_datetime"] == TO

    def test_the_item_info_and_origin_are_recorded(self):
        """The item info and origin are recorded."""
        processor, _ = self.build(FakeHilltopClient(xml=make_xml([1.0, 2.0, 3.0])))

        processor.load_data()

        assert processor.standard_item_info["units"] == "hPa"
        assert processor.standard_origin["provider"] == "horizons-hilltop"
        assert processor.standard_origin["source_tag"] == "HTP"
        assert processor.standard_origin["hts"] == HTS

    def test_the_origin_url_is_the_real_request(self):
        """The origin url is the real request."""
        processor, _ = self.build(FakeHilltopClient(xml=make_xml([1.0, 2.0, 3.0])))

        processor.load_data()

        url = processor.standard_origin["request_url"]
        assert url.startswith(f"{BASE_URL}/{HTS}?")
        assert "Request=GetData" in url
        assert "Atmospheric%20Pressure" in url

    def test_a_divisor_is_applied_once_by_whurl_and_not_again(self):
        """A divisor is applied once by whurl and not again."""
        xml = make_xml([50.0, 60.0, 70.0], divisor=10)
        processor, _ = self.build(FakeHilltopClient(xml=xml))

        processor.load_data()

        assert list(processor.standard_data["Raw"]) == [5.0, 6.0, 7.0]

    def test_the_provider_is_left_open(self):
        """The provider is left open."""
        processor, client = self.build(FakeHilltopClient(xml=make_xml([1.0, 2.0, 3.0])))

        processor.load_data()
        processor.load_data()

        assert client.closed is False


class TestWhenThereIsNoData:
    """When there is no data."""

    def test_the_frame_stays_empty(self):
        """The frame stays empty."""
        client = FakeHilltopClient(error=NO_DATA_ERROR)
        processor = Processor(make_run_config(), provider_with(client))

        processor.load_data()

        assert processor.standard_data.empty

    def test_the_issue_carries_a_url_to_paste_into_a_browser(self):
        """The issue carries a url to paste into a browser."""
        client = FakeHilltopClient(error=NO_DATA_ERROR)
        processor = Processor(make_run_config(), provider_with(client))

        processor.load_data()

        issues = processor.processing_issues
        (issue,) = issues[issues["code"] == "MSD"].itertuples()

        assert issue.message_type == "error"
        assert f"{BASE_URL}/{HTS}?" in issue.comment
        assert "Request=GetData" in issue.comment


class TestAMisspeltMeasurementOrSite:
    """A typo must stop the run, not look like a quiet period.

    The server's three "nothing" answers reach the Processor through the real
    provider here. Only an empty RANGE is quiet; a wrong measurement or site is
    an error that says what was wrong, and nothing is stored.
    """

    def test_a_wrong_measurement_is_an_error_naming_it(self):
        """A wrong measurement is an error naming it."""
        client = FakeHilltopClient(error=NO_DATA_SOURCE_ERROR)
        processor = Processor(
            make_run_config(standard_measurement_name="Atmospheric Pressurk"),
            provider_with(client),
        )

        with pytest.raises(DataProviderError, match="Atmospheric Pressurk") as caught:
            processor.load_data()

        assert "no data source" in str(caught.value).lower()
        assert "No Data Source for" in str(caught.value)

    def test_a_wrong_site_is_an_error_naming_it(self):
        """A wrong site is an error naming it."""
        client = FakeHilltopClient(error=NO_SITE_ERROR)
        processor = Processor(
            make_run_config(site="Manawatu at Keachers Bollege"),
            provider_with(client),
        )

        with pytest.raises(DataProviderError, match="Keachers Bollege") as caught:
            processor.load_data()

        assert "does not know the site" in str(caught.value)

    def test_the_error_carries_the_real_url_to_paste_into_a_browser(self):
        """The error carries the real URL to paste into a browser."""
        client = FakeHilltopClient(error=NO_DATA_SOURCE_ERROR)
        processor = Processor(make_run_config(), provider_with(client))

        with pytest.raises(DataProviderError) as caught:
            processor.load_data()

        assert f"{BASE_URL}/{HTS}?" in str(caught.value)
        assert "Request=GetData" in str(caught.value)

    def test_nothing_is_stored_and_no_issue_is_recorded(self):
        """Nothing is stored and no issue is recorded."""
        client = FakeHilltopClient(error=NO_DATA_SOURCE_ERROR)
        processor = Processor(make_run_config(), provider_with(client))
        issues_before = len(processor.processing_issues)

        with pytest.raises(DataProviderError):
            processor.load_data()

        assert processor.standard_data.empty
        assert processor.standard_origin is None
        assert len(processor.processing_issues) == issues_before

    def test_import_standard_stops_on_a_typo_too(self):
        """import_standard stops on a typo too."""
        client = FakeHilltopClient(error=NO_DATA_SOURCE_ERROR)
        processor = Processor(make_run_config(), provider_with(client))

        with pytest.raises(DataProviderError):
            processor.import_standard(measurement="Atmospheric Pressurk")

    def test_only_an_empty_range_is_quiet(self):
        """Only an empty range is quiet."""
        client = FakeHilltopClient(error=NO_DATA_ERROR)
        processor = Processor(make_run_config(), provider_with(client))

        processor.load_data()  # no exception

        assert processor.standard_data.empty


class TestWhenTheNameIsWrong:
    """When the name is wrong."""

    def test_the_provider_error_reaches_the_caller(self):
        # Data came back, but not under this name: a typo, almost certainly.
        """The provider error reacher the caller."""
        xml = make_xml([1.0, 2.0, 3.0], measurement="Something Else")
        client = FakeHilltopClient(xml=xml)
        processor = Processor(make_run_config(), provider_with(client))

        with pytest.raises(DataProviderError, match="Something Else"):
            processor.load_data()


    def test_nothing_is_stored(self):
        """Nothing is stored."""
        xml = make_xml([1.0, 2.0, 3.0], measurement="Something Else")
        client = FakeHilltopClient(xml=xml)
        processor = Processor(make_run_config(), provider_with(client))

        with pytest.raises(DataProviderError):
            processor.load_data()

        assert processor.standard_data.empty
        assert processor.standard_origin is None

        assert processor.standard_data.empty
        assert processor.standard_origin is None
