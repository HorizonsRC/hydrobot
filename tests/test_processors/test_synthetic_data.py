"""Tests for replacing data with synthetic data from another site.

HOW THESE TESTS WORK
--------------------
``use_synthetic_data_from_alternative_site`` replaces a stretch of the run's
own series with scaled readings from another site.

The provider is a FakeProvider that answers differently for each
``(site, measurement)``, so the run's own series and the other site's series
can be told appart.
"""

import numpy as np
import pandas as pd

from hydrobot.processors.processor import Processor
from tests.fake_provider import (
    MEASUREMENT,
    FakeProvider,
    make_run_config,
    make_standard,
)

OTHER_SITE = "Manawatu at Somewhere Else"


def build(alt_standard=None, **config):
    """Return ``(processor, provider)`` with the run's own series loaded.

    The run's series is thirteen readings, 100 to 112, every five minutes from
    00:00. ``alt_standard`` is what the other site answers with.
    """
    own = make_standard([100.0 + i for i in range(13)])
    provider = FakeProvider(
        standard=own,
        standard_by_series=(
            {(OTHER_SITE, MEASUREMENT): alt_standard} if alt_standard else {}
        ),
    )
    processor = Processor(make_run_config(**config), provider)
    processor.load_data()
    return processor, provider

def alt_standard():
    """Three readings, 10, 20, and 30, from 00:17 (off the run's own times)."""
    return make_standard([10.0, 20.0, 30.0], start="2025-01-01 00:17")


def replace(processor, **options):
    """Replace 00:15 to 00:45, doubling the other site's readings and adding 1."""
    processor.use_synthetic_data_from_alternative_site(
        OTHER_SITE,
        "2025-01-01 00:15",
        "2025-01-01 00:45",
        multiplier=2,
        offset=1,
        **options,
    )


class TestWhatIsAsked:
    """What the other site is asked for."""

    def test_it_asks_the_other_site_for_the_runs_measurement_and_the_range(self):
        """It asks the other site for the run's measurement and the range."""
        processor, provider = build(alt_standard())

        replace(processor)

        assert provider.calls[-1] == (
            "get_standard",
            OTHER_SITE,
            MEASUREMENT,
            pd.Timestamp("2025-01-01 00:15"),
            pd.Timestamp("2025-01-01 00:45"),
        )

    def test_a_different_measurement_keeps_the_original_data_source(self):
        """A different measurement keeps the original data source."""
        processor, provider = build(alt_standard())

        replace(processor, alt_measurement="Water Temperature")

        assert provider.calls[-1][2] == f"Water Temperature [{MEASUREMENT}]"

    def test_a_differe_data_source_keeps_the_original_measurement(self):
        """A different data source keeps the original measurement."""
        processor, provider = build(alt_standard())

        replace(processor, alt_datasource="Water Temp")

        assert provider.calls[-1][2] == f"{MEASUREMENT} [Water Temp]"

    def test_both_can_be_changed(self):
        """Both can be changed."""
        processor, provider = build(alt_standard())

        replace(
            processor, alt_measurement="Water Temperature", alt_datasource="Water Temp"
        )

        assert provider.calls[-1][2] == "Water Temperature [Water Temp]"

    def test_the_other_series_is_read_as_the_server_has_it(self):
        """The other series is read as the server has it."""
        # The run has a frequency, but the other site's series is not
        # regularised to it: the rows are just the readings it has.
        processor, _ = build(alt_standard(), frequency="5min")
        before = len(processor.standard_data)

        replace(processor)

        assert len(processor.standard_data) == before + 3


class TestWhatChanges:
    """What the replacement does to the run's series."""

    def test_the_other_sites_readings_are_scaled_and_added(self):
        """The other site's readings are scaled and added."""
        processor, _ = build(alt_standard())

        replace(processor)

        data = processor.standard_data
        alt_rows = data.loc[
            [
                pd.Timestamp("2025-01-01 00:17"),
                pd.Timestamp("2025-01-01 00:22"),
                pd.Timestamp("2025-01-01 00:27"),
            ],
            "Value",
        ]
        assert list(alt_rows) == [21.0, 41.0, 61.0]  # 10, 20, 30, doubled, plus 1

    def test_the_runs_own_values_inside_the_range_are_blanked(self):
        """The run's own values inside the range are blanked."""
        processor, _ = build(alt_standard())

        replace(processor)

        data = processor.standard_data
        own = data.loc[
            [
                pd.Timestamp("2025-01-01 00:20"),
                pd.Timestamp("2025-01-01 00:25"),
                pd.Timestamp("2025-01-01 00:30"),
            ],
            "Value",
        ]
        assert own.isna().all()

    def test_values_outside_the_range_are_untouched(self):
        """Values outside the range are untouched."""
        processor, _ = build(alt_standard())

        replace(processor)

        data = processor.standard_data
        assert data.loc[pd.Timestamp("2025-01-01 00:00"), "Value"] == 100.0
        assert data.loc[pd.Timestamp("2025-01-01 01:00"), "Value"] == 112.0

    def test_the_raw_colunm_is_not_touched(self):
        """The Raw column is not touched."""
        processor, _ = build(alt_standard())
        raw_before = processor.standard_data["Raw"].copy()

        replace(processor)

        kept = processor.standard_data.loc[raw_before.index, "Raw"]
        assert not np.isnan(kept).any()
        assert kept.equals(raw_before)

    def test_the_result_stays_in_time_order(self):
        """The result stays in time order."""
        processor, _ = build(alt_standard())

        replace(processor)

        assert processor.standard_data.index.is_monotonic_increasing

    def test_the_runs_frequency_is_not_changed(self):
        """The run's frequency is not changed."""
        processor, _ = build(alt_standard(), frequency="5min")

        replace(processor)

        assert processor.frequency == "5min"
