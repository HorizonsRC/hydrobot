"""Tests for reading standard data into a Processor.

HOW THESE TESTS WORK
--------------------
There are two methods, with different jobs:

*   ``import_standard(...)`` READS a series from the provider and RETURNS it as
    a standard frame. It stores nothing. That is what makes it usable for
    other series too (the dissolved oxygen processor reads atmospheric
    pressure and water temperature this way).
*   ``load_data()`` reads the run's OWN series with ``import_standard`` and
    STORES the result, along with what the provider said about it.

The provider is a FakeProvider (see tests/fake_provider.py), which records
what it was asked, so these tests can check the question as well as the answer.
"""

from datetime import datetime

import numpy as np
import pandas as pd
import pytest

from hydrobot.processors.frames import EMPTY_STANDARD_DATA
from hydrobot.processors.processor import Processor
from hydrobot.providers.types import DataProviderError
from tests.fake_provider import (
    MEASUREMENT,
    SITE,
    FakeProvider,
    empty_standard,
    make_origin,
    make_run_config,
    make_standard,
)


def build(standard=None, error=None, **overrides):
    """Return ``(processor, provider)`` with the provider holding ``standard``."""
    provider = FakeProvider(standard=standard, standard_error=error)
    return Processor(make_run_config(**overrides), provider), provider


def issues_with(processor, code):
    """Return the processing issues that have this code."""
    frame = processor.processing_issues
    return frame[frame["code"] == code]


class TestWhatIsAsked:
    """What is asked."""

    def test_the_provider_is_asked_for_the_runs_series_and_range(self):
        """The provider is asked for the run's series and range."""
        processor, provider = build(make_standard([1.0, 2.0, 3.0]))

        processor.import_standard()

        assert provider.calls == [
            (
                "get_standard",
                SITE,
                MEASUREMENT,
                datetime(2025, 1, 1, 0, 0),
                datetime(2025, 1, 1, 1, 0),
            )
        ]

    def test_the_dates_passed_are_real_datetimes(self):
        """The dates passed are real datetimes."""
        processor, provider = build(make_standard([1.0, 2.0, 3.0]))

        processor.import_standard()

        _, _, _, from_date, to_date = provider.calls[0]
        assert isinstance(from_date, datetime)
        assert isinstance(to_date, datetime)

    def test_another_series_can_be_asked_for(self):
        # How companion series are read (atmospheric pressure, say).
        """Another series can be asked for."""
        processor, provider = build(make_standard([1.0, 2.0, 3.0]))

        processor.import_standard(site="Other Site", measurement="Water Temperature")

        assert provider.calls[0][1:3] == ("Other Site", "Water Temperature")

    def test_another_range_can_be_asked_for(self):
        """Another range can be asked for."""
        processor, provider = build(make_standard([1.0, 2.0, 3.0]))

        processor.import_standard(
            from_date="2024-06-01 00:00", to_date=pd.Timestamp("2024-06-02 12:30")
        )

        assert provider.calls[0][3:] == (
            datetime(2024, 6, 1, 0, 0),
            datetime(2024, 6, 2, 12, 30),
        )

    def test_the_provider_is_asked_once(self):
        """The provider is asked once."""
        processor, provider = build(make_standard([1.0, 2.0, 3.0]))

        processor.import_standard()

        assert len(provider.calls) == 1

    def test_the_provider_is_left_open(self):
        """The provider is left open."""
        processor, provider = build(make_standard([1.0, 2.0, 3.0]))

        processor.import_standard()
        processor.import_standard()

        assert provider.closed is False


class TestWhatComesBack:
    """What comes back."""

    def test_it_is_a_standard_frame(self):
        """It is a standard frame."""
        processor, _ = build(make_standard([1000.0, 1001.0, 1002.0]))

        frame = processor.import_standard()

        assert list(frame.columns) == ["Raw", "Value", "Changes", "Remove"]
        assert list(frame["Raw"]) == [1000.0, 1001.0, 1002.0]
        assert frame.index.name == "Time"

    def test_nothing_is_stored(self):
        """Nothing is stored."""
        processor, _ = build(make_standard([1000.0, 1001.0, 1002.0]))

        processor.import_standard()

        assert processor.standard_data.empty

    def test_the_run_is_not_changed_by_reading_another_series(self):
        # The old method set the processor's frequency whenever it inferred
        # one, so reading a companion series with a different frequency
        # silently changed the main series' frequency too.
        """The run is not changed by reading another series."""
        processor, _ = build(make_standard([1.0, 2.0, 3.0], step_minutes=60))
        assert processor.frequency is None

        processor.import_standard(measurement="Water Temperature")

        assert processor.frequency is None

    def test_a_provider_error_is_not_swallowed(self):
        """A provider error is not swallowed."""
        error = DataProviderError("Standard data not found under name 'Typo'.")
        processor, _ = build(error=error)

        with pytest.raises(DataProviderError, match="Typo"):
            processor.import_standard()

    def test_a_failed_read_leaves_no_processing_issue_behind(self):
        """A failed read leaves no processing issue behind."""
        processor, _ = build(error=DataProviderError("nope"))
        before = len(processor.processing_issues)

        with pytest.raises(DataProviderError):
            processor.import_standard()

        assert len(processor.processing_issues) == before


class TestFrequency:
    """Frequency."""

    def test_a_configured_frequency_fills_the_gaps(self):
        """A configured frequency fills the index gaps."""
        standard = make_standard([1.0, 2.0, 4.0], positions=[0, 1, 3])
        processor, _ = build(standard, frequency="5min")

        frame = processor.import_standard()

        assert len(frame) == 4
        assert np.isnan(frame["Raw"].iloc[2])

    def test_an_inferred_frequency_is_reported_as_an_issue(self):
        """An inferred frequency is reported as an issue."""
        standard = make_standard([1.0, 2.0, 4.0, 5.0], positions=[0, 1, 3, 4])
        processor, _ = build(standard)

        processor.import_standard()

        (issue,) = issues_with(processor, "IRR").itertuples()
        assert issue.comment == "frequency inferred as 5min"
        assert issue.message_type == "info"

    def test_irregular_data_is_left_alone_and_reported(self):
        """Irregular data is left alone and reported."""
        standard = make_standard([1.0, 2.0, 4.0], positions=[0, 1, 3])
        processor, _ = build(standard, infer_frequency=False)

        frame = processor.import_standard()

        assert len(frame) == 3
        (issue,) = issues_with(processor, "IRR").itertuples()
        assert MEASUREMENT in issue.comment

    def test_too_few_points_to_infer_is_a_warning_not_a_crash(self):
        """Too few points to infer is a warning, not a crash."""
        processor, _ = build(make_standard([1.0, 2.0]))

        frame = processor.import_standard()

        assert len(frame) == 2
        (issue,) = issues_with(processor, "IRR").itertuples()
        assert issue.message_type == "warning"


class TestNoData:
    """No data."""

    def test_the_frame_is_empty(self):
        """The frame is empty."""
        processor, _ = build(empty_standard())

        frame = processor.import_standard()

        pd.testing.assert_frame_equal(frame, EMPTY_STANDARD_DATA)

    def test_an_error_issue_is_reported_with_the_request_url(self):
        """An error issue is reported with the request url."""
        origin = make_origin(request_url="http://example.invalid/x.hts?Site=Typo")
        processor, _ = build(empty_standard(origin))

        processor.import_standard()

        (issue,) = issues_with(processor, "MSD").itertuples()
        assert issue.message_type == "error"
        assert issue.series_type == "Standard"
        assert "http://example.invalid/x.hts?Site=Typo" in issue.comment

    def test_the_issue_carries_the_range_that_was_asked_for(self):
        """The issue carries the range that was asked for."""
        origin = make_origin()
        processor, _ = build(empty_standard(origin))

        processor.import_standard()

        (issue,) = issues_with(processor, "MSD").itertuples()
        assert issue.start_time == origin["from_date"]
        assert issue.end_time == origin["to_date"]

    def test_no_data_is_not_an_exception(self):
        # A quiet period is normal. The caller decides what it means.
        """No data is not an exception."""
        processor, _ = build(empty_standard())

        processor.import_standard()


class TestLoadData:
    """Load data."""

    def test_it_stores_the_series_in_standard_data(self):
        """It stores the series in standard data."""
        processor, _ = build(make_standard([1000.0, 1001.0, 1002.0]))

        processor.load_data()

        assert list(processor.standard_data["Raw"]) == [1000.0, 1001.0, 1002.0]
        assert list(processor.standard_data["Value"]) == [1000.0, 1001.0, 1002.0]

    def test_it_asks_for_the_runs_own_series(self):
        """It asks for the runs own series."""
        processor, provider = build(make_standard([1.0, 2.0, 3.0]))

        processor.load_data()

        assert provider.calls[0][1:3] == (SITE, MEASUREMENT)

    def test_a_second_load_replaces_the_first(self):
        """A second load replaces the first."""
        processor, provider = build(make_standard([1.0, 2.0, 3.0]))
        processor.load_data()

        provider.standard = make_standard([7.0, 8.0, 9.0, 10.0])
        processor.load_data()

        assert list(processor.standard_data["Raw"]) == [7.0, 8.0, 9.0, 10.0]

    def test_another_range_can_be_loaded(self):
        """Another range can be loaded."""
        processor, provider = build(make_standard([1.0, 2.0, 3.0]))

        processor.load_data(from_date="2024-06-01 00:00", to_date="2024-06-02 00:00")

        assert provider.calls[0][3:] == (
            datetime(2024, 6, 1, 0, 0),
            datetime(2024, 6, 2, 0, 0),
        )

    def test_an_inferred_frequency_becomes_the_runs_frequency(self):
        """An inferred frequency becomes the runs frequency."""
        processor, _ = build(make_standard([1.0, 2.0, 3.0]))

        processor.load_data()

        assert processor.frequency == "5min"

    def test_a_configured_frequency_is_kept(self):
        """A configured frequency is kept."""
        processor, _ = build(make_standard([1.0, 2.0, 3.0]), frequency="5min")

        processor.load_data()

        assert processor.frequency == "5min"

    def test_irregular_data_leaves_the_frequency_unset(self):
        """Irregular data leaves the frequency unset."""
        processor, _ = build(make_standard([1.0, 2.0, 3.0]), infer_frequency=False)

        processor.load_data()

        assert processor.frequency is None

    def test_the_item_info_comes_from_what_the_provider_said(self):
        """The item info comes from what the provider said."""
        processor, _ = build(make_standard([1.0, 2.0, 3.0], divisor=10))

        processor.load_data()

        assert processor.standard_item_info == {
            "item_name": MEASUREMENT,
            "item_format": "F",
            "divisor": 10,
            "units": "hPa",
            "number_format": "####.#",
        }

    def test_where_the_data_came_from_is_kept(self):
        """Where the data came from is kept."""
        origin = make_origin(request_url="http://example.invalid/the-request")
        processor, _ = build(make_standard([1.0, 2.0, 3.0], origin=origin))

        processor.load_data()

        assert processor.standard_origin == origin

    def test_no_data_leaves_the_frame_empty_and_the_item_info_alone(self):
        """No data leaves the frame empty and the item info alone."""
        processor, _ = build(empty_standard())
        info_before = dict(processor.standard_item_info)

        processor.load_data()

        assert processor.standard_data.empty
        assert processor.standard_item_info == info_before

    def test_no_data_still_records_where_it_looked(self):
        """No data still records where it looked."""
        origin = make_origin(request_url="http://example.invalid/looked-here")
        processor, _ = build(empty_standard(origin))

        processor.load_data()

        assert processor.standard_origin == origin

    def test_no_data_is_reported(self):
        """No data is reported."""
        processor, _ = build(empty_standard())

        processor.load_data()

        assert len(issues_with(processor, "MSD")) == 1

    def test_the_run_config_is_not_changed(self):
        """The run config is not changed."""
        processor, _ = build(make_standard([1.0, 2.0, 3.0]))
        before = dict(processor.run_config)

        processor.load_data()

        assert processor.run_config == before

    def test_a_provider_error_leaves_the_processor_as_it_was(self):
        """A provider error leaves the processor as it was."""
        processor, _ = build(error=DataProviderError("nope"))

        with pytest.raises(DataProviderError):
            processor.load_data()

        assert processor.standard_data.empty
        assert processor.frequency is None


class TestFrequencyOverrides:
    """Frequency overrides for a single read.

    A read can bring its own frequency settings. ``do_processor`` reads
    companion series with their own explicit frequencies, and the synthetic
    data method reads another site's series as it is. The rule: give neither
    ``frequency`` nor ``infer_frequency`` and the run's settings apply; give
    either and the read's own settings replace the run's, and only those.
    """

    GAPPY = {"values": [1.0, 2.0, 4.0], "positions": [0, 1, 3]}

    def test_a_given_frequency_replaces_the_runs(self):
        """A given frequency replaces the run's."""
        processor, _ = build(
            make_standard(**self.GAPPY, step_minutes=15), frequency="5min"
        )

        frame = processor.import_standard(frequency="15min", infer_frequency=False)

        assert len(frame) == 4  # regularised to 15 minutes, not the run's 5

    def test_turning_inference_off_gives_irregular_data(self):
        """Turning inference off gives irregular data."""
        # The run has a frequency, but this read says "as the server has it".
        processor, _ = build(make_standard(**self.GAPPY), frequency="5min")

        frame = processor.import_standard(infer_frequency=False)

        assert len(frame) == 3

    def test_turning_inference_on_infers_even_if_the_run_does_not(self):
        """Turning inference on infers even if the run does not."""
        processor, _ = build(make_standard(**self.GAPPY), infer_frequency=False)

        frame = processor.import_standard(infer_frequency=True)

        assert len(frame) == 4

    def test_a_frequency_alone_is_used(self):
        """A frequency alone is used."""
        processor, _ = build(make_standard(**self.GAPPY), infer_frequency=False)

        frame = processor.import_standard(frequency="5min")

        assert len(frame) == 4

    def test_giving_neither_uses_the_runs_settings(self):
        """Giving neither uses the run's settings."""
        processor, _ = build(make_standard(**self.GAPPY), frequency="5min")

        assert len(processor.import_standard()) == 4

    def test_an_override_does_not_change_the_runs_own_settings(self):
        """An override does not change the run's own settings."""
        processor, _ = build(make_standard(**self.GAPPY), frequency="5min")

        processor.import_standard(frequency="15min", infer_frequency=False)

        assert processor.frequency == "5min"
        assert processor.infer_frequency is True
