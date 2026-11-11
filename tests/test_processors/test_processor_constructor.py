"""Tests for building a Processor from a run config and a provider.

HOW THESE TESTS WORK
--------------------
A Processor is build from two things: a RUN CONFIG (the dict ``resolve()``
produces; see tests/fake_provider.py ``make_run_config``) and a PROVIDER. The
provider here is a FakeProvider that remembers every call.

The main change from the old constructor is that building a Processor no
longer touches a server. It used to open Hilltop connections and fetch all the
data before returning; now ``load_data()`` does that, as a separate step. So a
Processor can be built, and tested, without a provider that has any data.
"""
from hydrobot.data_acquisition import convert_inspection_expiry
from hydrobot.utils import infer_frequency
import whurl

import pandas as pd
import pytest

import hydrobot
from hydrobot import data_sources
from hydrobot.processors.frames import (
    EMPTY_CHECK_DATA,
    EMPTY_QUALITY_DATA,
    EMPTY_STANDARD_DATA,
)
from hydrobot.processors.processor import Processor
from tests.fake_provider import FakeProvider, make_run_config


def build(provider=None, **overrides) -> Processor:
    """Build a Processor froma complete run config plus ``overrides``."""
    return Processor(make_run_config(**overrides), provider or FakeProvider())


class TestBuildingDoesNotTouchTheProvider:
    """Building does not touch the provider."""

    def test_no_calls_are_made(self):
        """No calls are made."""
        provider = FakeProvider()

        Processor(make_run_config(), provider)

        assert provider.calls == []

    def test_a_provider_with_no_data_is_fine(self):
        # FakeProvider raises if asked for data it was not given, so this
        # passing proves the constructor never asks.
        """A provider with no data is fine."""
        build(FakeProvider(standard=None))

    def test_the_provider_is_not_closed(self):
        """The provider is not closed."""
        provider = FakeProvider()

        build(provider)

        assert provider.closed is False

    def test_the_processor_keeps_the_provider_it_was_given(self):
        """The processor keeps the provider it was given."""
        provider = FakeProvider()

        assert build(provider).provider is provider


class TestAnIncompleteRunConfig:
    """An incomplete run config."""

    def test_missing_keys_are_all_named_at_once(self):
        """Missing keys are all named at once."""
        config = make_run_config()
        del config["from_date"]
        del config["data_family"]

        with pytest.raises(ValueError, match="data_family") as caught:
            Processor(config, FakeProvider())

        assert "from_date" in str(caught.value)

    @pytest.mark.parametrize(
        "key",
        ["site", "standard_measurement_name", "data_family", "from_date", "to_date"],
    )
    def test_each_required_key_is_required(self, key):
        """Each required key is required."""
        config = make_run_config()
        del config[key]

        with pytest.raises(ValueError, match=key):
            Processor(config, FakeProvider())

    def test_a_key_set_to_none_counts_as_missing(self):
        # A saved config can hold ``from_date:`` with nothing after it.
        """A key set to none counts as missing."""
        with pytest.raises(ValueError, match="from_date"):
            build(from_date=None)

    def test_the_message_says_where_dates_come_from(self):
        """The message says where dates come from."""
        with pytest.raises(ValueError, match="resolve"):
            build(to_date=None)

    def test_a_date_that_is_not_a_date_is_named(self):
        """A date that is not a date is named."""
        with pytest.raises(ValueError, match="from_date"):
            build(from_date="tomorrow and tomorrow and tomorrow")

    def test_from_date_after_to_date_is_refused(self):
        """From date after to date is refused."""
        with pytest.raises(ValueError, match="from_date"):
            build(from_date="2025-02-01 00:00", to_date="2025-01-01 00:00")

    def test_an_unknown_data_family_is_an_error(self):
        """An unknown data family is an error."""
        with pytest.raises(KeyError):
            build(data_family="not_a_real_family")


class TestWhatItReads:
    """What it reads."""

    def test_identity_and_dates(self):
        """Identity and dates."""
        processor = build()

        assert processor.site == "Manawatu at Teachers College"
        assert processor.standard_measurement_name == "Atmospheric Pressure"
        assert processor.data_family == "atmospheric_pressure"
        assert processor.from_date == pd.Timestamp("2025-01-01 00:00")
        assert processor.to_date == pd.Timestamp("2025-01-01 01:00")

    def test_dates_are_timestamps(self):
        """Dates are timestamps."""
        processor = build()

        assert isinstance(processor.from_date, pd.Timestamp)
        assert isinstance(processor.to_date, pd.Timestamp)

    def test_optional_settings_are_taken_from_the_config(self):
        """Optional settings are taken from the config."""
        processor = build(
            frequency="5min",
            infer_frequency=False,
            defaults={"gap_limit": 12},
            export_file_name="out.xml",
            layer=500,
        )

        assert processor.frequency == "5min"
        assert processor.infer_frequency is False
        assert processor.defaults == {"gap_limit": 12}
        assert processor.export_file_name == "out.xml"
        assert processor.layer == 500

    def test_there_is_no_depth_any_more(self):
        # "depth" became "layer", and nothing has to be a depth.
        """There is no depth any more."""
        assert not hasattr(build(), "depth")

    def test_unknown_keys_are_ignored(self):
        # Real run configs carry plenty the Processor does not read.
        """Unknown keys are ignored."""
        build(analyst_name="Speve", logfile="x.csv", inspection_expiry={500: 2})

    def test_the_run_config_is_kept_as_an_independent_copy(self):
        """The run config is kept as an independent copy."""
        config = make_run_config(defaults={"gap_limit": 12})
        processor = Processor(config, FakeProvider())

        config["defaults"]["gap_limit"] = 999
        config["site"] = "Somewhere else"

        assert processor.run_config["defaults"] == {"gap_limit": 12}
        assert processor.run_config["site"] == "Manawatu at Teachers College"

    def test_defaults_given_in_the_config_are_not_shared(self):
        """Defaults given in the config are not shared."""
        config = make_run_config(defaults={"gap_limit": 12})
        processor = Processor(config, FakeProvider())

        processor.defaults["gap_limit"] = 1

        assert config["defaults"]["gap_limit"] == 12


class TestMeasurementNames:
    """Measurement names."""

    def test_a_plain_name_is_its_own_data_source(self):
        """A plain name is its own data source."""
        processor = build(standard_measurement_name="Atmospheric Pressure")

        assert processor.standard_item_name == "Atmospheric Pressure"
        assert processor.standard_data_source_name == "Atmospheric Pressure"

    def test_a_bracketed_name_is_split_into_item_and_data_source(self):
        """A bracketed name is split into item and data source."""
        processor = build(standard_measurement_name="Water Temperature [Water Temp]")

        assert processor.standard_item_name == "Water Temperature"
        assert processor.standard_data_source_name == "Water Temp"

    def test_the_archive_name_defaults_to_the_standard_name(self):
        """The archive name defaults to the standard name."""
        processor = build()

        assert processor.archive_standard_measurement_name == "Atmospheric Pressure"

    def test_the_archive_name_can_differ(self):
        """The archive name can differ."""
        processor = build(archive_standard_measurement_name="AP [Archive AP]")

        assert processor.archive_standard_measurement_name == "AP [Archive AP]"
        assert processor.archive_standard_item_name == "AP"
        assert processor.archive_standard_data_source_name == "Archive AP"

    def test_a_check_name_is_only_known_if_the_config_has_one(self):
        """A check name is only known if the config has one."""
        assert build().check_measurement_name is None
        assert (
            build(
                check_measurement_name="Check Pressure [Atmospheric Pressure]"
            ).check_measurement_name
            == "Check Pressure [Atmospheric Pressure]"
        )

    def test_the_check_item_is_split_like_the_others(self):
        """The check item name is split like the others."""
        processor = build(
            check_measurement_name="Check Pressure [Atmospheric Pressure]"
        )

        assert processor.check_item_name == "Check Pressure"
        assert processor.check_data_source_name == "Atmospheric Pressure"


class TestStartingState:
    """Starting state."""

    def test_the_frames_start_empty_with_the_expected_columns(self):
        """The frames start empty with the expected columns."""
        processor = build()

        pd.testing.assert_frame_equal(processor.standard_data, EMPTY_STANDARD_DATA)
        pd.testing.assert_frame_equal(processor.check_data, EMPTY_CHECK_DATA)
        pd.testing.assert_frame_equal(processor.quality_data, EMPTY_QUALITY_DATA)

    def test_each_processor_gets_its_own_frames(self):
        """Each processor gets its own frames."""
        first, second = build(), build()

        first.standard_data["Raw"] = 1.0

        assert "Raw" in second.standard_data.columns
        assert second.standard_data.empty

    def test_the_shared_templates_are_not_the_processors_frames(self):
        """The shared templates are not the processors frames."""
        processor = build()

        processor.standard_data.loc[pd.Timestamp("2025-01-01"), "Raw"] = 1.0

        assert EMPTY_STANDARD_DATA.empty

    def test_the_quality_code_evaluator_comes_from_the_data_family(self):
        """The quality code evaluator comes from the data family."""
        processor = build(data_family="atmospheric_pressure")

        assert isinstance(
            processor.quality_code_evaluator, data_sources.QualityCodeEvaluator
        )

    def test_the_constant_check_shift_is_applied_to_it(self):
        """The constant check shift is applied to it."""
        processor = build(standard_measurement_name="Water Temperature [Water Temp]")

        assert processor.standard_item_info == {
            "item_name": "Water Temperature",
            "item_format": "F",
            "divisor": 1,
            "units": "",
            "number_format": "###.##"
        }

    def test_the_processing_issues_start_with_the_hydrobot_version(self):
        """The processing issues start with the hydrobot version."""
        processor = build()

        issues = processor.processing_issues
        assert len(issues) == 1
        assert issues["comment"].iloc[0] == f"Hydrobot Version: {hydrobot.__version__}"
        assert issues["message_type"].iloc[0] == "info"

