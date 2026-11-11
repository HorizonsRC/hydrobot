"""Tests for turning a provider's answer into a standard frame.

HOW THESE TESTS WORK
--------------------
``standard_frame`` is a pure function: a provider's ``StandardData`` goes in,
a frame comes out, plus a list of notes for the Processor to report. There is
no provider, server or Processor to fake, so each test is just "this input
gives this output".

The input data is built by tests/fake_provider.py, which runs real XML through
whurl's real parser. So the shapes here are the shapes the real provider hands
over, not hand-made DataFrames that could drift.
"""

import numpy as np
import pandas as pd
import pytest

from hydrobot.processors.frames import EMPTY_STANDARD_DATA
from hydrobot.processors.importing import (
    FREQUENCY_CODE,
    NO_DATA_CODE,
    standard_frame,
)
from tests.fake_provider import MEASUREMENT, empty_standard, make_origin, make_standard


def build(standard, *, frequency=None, infer_frequency=True):
    """Build a standard frame with the settings most tests share."""
    return standard_frame(
        standard,
        measurement=MEASUREMENT,
        frequency=frequency,
        infer_frequency=infer_frequency,
    )

class TestTheFrame:
    """The frame."""

    def test_it_has_the_columns_the_rest_of_the_processor_expects(self):
        """It has the columns the rest of the processor expects."""
        result = build(make_standard([1000.0, 1001.0, 1002.0]))

        assert list(result.data.columns) == list(EMPTY_STANDARD_DATA.columns)
        assert list(result.data.columns) == ["Raw", "Value", "Changes", "Remove"]

    def test_the_index_is_called_time(self):
        # whurl calls it "DateTime". The frame has always been "Time".
        # I'm leaving this discrepancy as a smoke test to make sure
        # all whurl calls are handled correctly.
        """The index is called time."""
        result = build(make_standard([1000.0, 1001.0, 1002.0]))

        assert result.data.index.name == "Time"
        assert isinstance(result.data.index, pd.DatetimeIndex)

    def test_raw_and_value_start_out_equal(self):
        """Raw and value start out equal."""
        result = build(make_standard([1000.0, 1001.5, 1002.0]))

        assert list(result.data["Raw"]) == [1000.0, 1001.5, 1002.0]
        assert result.data["Value"].equals(result.data["Raw"])

    def test_changes_and_remove_start_empty(self):
        """Changes and remove start empty."""
        result = build(make_standard([1000.0, 1001.0, 1002.0]))

        assert result.data["Changes"].isna().all()
        assert result.data["Remove"].isna().all()

    def test_values_are_float64_and_not_stuffed_into_float32(self):
        # The old Processor cast to float32, which turns 998.4 into
        # 998.4000244140625. whurl already gives float64, and nothing needs
        # the loss.
        """Values are float64 and not stuffed into float32."""
        result = build(make_standard([998.4, 998.5, 998.6]))

        assert result.data["Raw"].dtype == "float64"
        assert result.data["Raw"].iloc[0] == 998.4

    def test_a_divisor_in_the_metadata_is_not_applied_again(self):
        # The provider's contract: the data is already scaled (whurl divided
        # 50, 60, and 70 by 10 while parsing). The metadata still says 10, for
        # information, and dividing by it again would be the bug.
        """A divisor in the metadata is not applied again."""
        standard = make_standard([50.0, 60.0, 70.0], divisor=10)

        assert standard.metadata["divisor"] == 10
        assert list(standard.data.iloc[:, 0]) == [5.0, 6.0, 7.0]

        result = build(standard)

        assert list(result.data["Raw"]) == [5.0, 6.0, 7.0]

    def test_a_blank_value_stays_nan(self):
        """A blank value stays nan."""
        result = build(make_standard([1000.0, None, 1002.0]))

        assert np.isnan(result.data["Raw"].iloc[1])
        assert result.data["Raw"].iloc[0] == 1000.0

    def test_only_the_first_column_is_used(self):
        """Only the first column is used."""
        standard = make_standard([1000.0, 1001.0, 1002.0])
        standard.data["Another item"] = [1, 2, 3]

        result = build(standard)

        assert list(result.data["Raw"]) == [1000.0, 1001.0, 1002.0]
        assert "Another item" not in result.data.columns

    def test_the_input_is_not_modified(self):
        """The input is not modified."""
        standard = make_standard([1000.0, None, 1002.0], positions=[0, 1, 3])
        before = standard.data.copy()

        build(standard, frequency="5min")

        pd.testing.assert_frame_equal(standard.data, before)

    def test_the_shared_empty_template_is_never_modified(self):
        """The shared empty template is never modified."""
        template_before = EMPTY_STANDARD_DATA.copy()

        build(make_standard([1000.0, 1001.0, 1002.0]))
        build(empty_standard())

        pd.testing.assert_frame_equal(EMPTY_STANDARD_DATA, template_before)


class TestGivenFrequency:
    """Given frequency."""

    def test_gaps_are_filled_with_nan(self):
        # Readings in slots 0, 1 and 3: nothing in slot 2.
        """Gaps are filled with nan."""
        standard = make_standard([1.0, 2.0, 4.0], positions=[0, 1, 3])

        result = build(standard, frequency="5min")

        assert len(result.data) == 4
        assert np.isnan(result.data["Raw"].iloc[2])
        assert result.frequency == "5min"

    def test_it_is_used_even_when_inference_is_also_on(self):
        # Teh old code warned whenever both were set, which is nearly every
        # real run. The given frequency simly wins.
        """It is used even when inference is also on."""
        standard = make_standard([1.0, 2.0, 4.0], positions=[0, 1, 3])

        result = build(standard, frequency="5min", infer_frequency=True)

        assert result.frequency == "5min"
        assert result.notes == []

    def test_it_works_with_too_few_points_to_infer(self):
        """It works with too few points to infer."""
        result = build(make_standard([1.0, 2.0]), frequency="5min")

        assert result.frequency == "5min"
        assert len(result.data) == 2


class TestInferredFrequency:
    """Inferred frequency."""

    def test_the_most_common_gap_is_used(self):
        # Slots 0, 1, 3, 4: gaps of 5, 10, 5 minutes. Five wins.
        """The most common gap is used."""
        standard = make_standard([1.0, 2.0, 4.0, 5.0], positions=[0, 1, 3, 4])

        result = build(standard)

        assert result.frequency == "5min"
        assert len(result.data) == 5
        assert np.isnan(result.data["Raw"].iloc[2])

    def test_it_is_reported_as_info(self):
        """It is reported as info."""
        result = build(make_standard([1.0, 2.0, 3.0]))

        (note,) = result.notes
        assert note.message_type == "info"
        assert note.code == FREQUENCY_CODE
        assert note.comment == "frequency inferred as 5min"

    def test_two_points_are_too_few_and_say_so(self):
        # pandas needs three points to infer. The old code crashed here with
        # "Need at least 3 dates to infer frequency", which is easy to hit when
        # reprocessing a short window.
        """Two points are too few and say so."""
        result = build(make_standard([1.0, 2.0]))

        assert result.frequency is None
        assert len(result.data) == 2
        (note,) = result.notes
        assert note.message_type == "warning"
        assert "too few" in note.comment

    def test_one_point_is_also_too_few(self):
        """One point is also too few."""
        result = build(make_standard([1.0]))

        assert result.frequency is None
        assert len(result.data) == 1


class TestIrregularData:
    """Irregular data."""

    def test_the_data_is_left_exactly_as_it_is(self):
        """The data is left exactly as it is."""
        standard = make_standard([1.0, 2.0, 4.0], positions=[0, 1, 3])

        result = build(standard, infer_frequency=False)

        assert result.frequency is None
        assert len(result.data) == 3

    def test_it_is_reported_as_info_naming_the_measurement(self):
        """It is reported as info naming the measurement."""
        result = build(make_standard([1.0, 2.0, 3.0]), infer_frequency=False)

        (note,) = result.notes
        assert note.message_type == "info"
        assert MEASUREMENT in note.comment


class TestNoData:
    """No data."""

    def test_the_frame_is_the_empty_template(self):
        """The frame is the empty template."""
        result = build(empty_standard())

        pd.testing.assert_frame_equal(result.data, EMPTY_STANDARD_DATA)

    def test_no_frequency_is_reported(self):
        """No frequency is reported."""
        assert build(empty_standard()).frequency is None

    def test_an_error_note_carries_the_request_url(self):
        """An error note carries the request url."""
        # So an analyst can paste it into a browser and see what the server said.
        origin = make_origin(request_url="http://example.invalid/x.hts?Site=Typo")

        result = build(empty_standard(origin))

        (note,) = result.notes
        assert note.message_type == "error"
        assert note.code == NO_DATA_CODE
        assert note.series_type == "Standard"
        assert "http://example.invalid/x.hts?Site=Typo" in note.comment

    def test_the_note_carries_the_range_that_was_asked_for(self):
        """The note carries the range that was asked for."""
        origin = make_origin()

        (note,) = build(empty_standard(origin)).notes

        assert note.start_time == origin["from_date"]
        assert note.end_time == origin["to_date"]

    def test_an_empty_read_with_no_origin_still_gives_an_error_note(self):
        # The contract says an origin is always recorded. Reporting must not
        # crash if a provider forgets, because that would hide the real problem.
        """An empty read with no origin still gives an error note."""
        standard = empty_standard()
        standard.metadata.clear()

        (note,) = build(standard).notes

        assert note.message_type == "error"
        assert "unknown request" in note.comment

    def test_a_frame_with_columns_but_no_rows_is_also_no_data(self):
        """A frame with columns but no rows is also no data."""
        standard = make_standard([1.0, 2.0, 3.0])
        standard.data = standard.data.iloc[0:0]

        result = build(standard)

        assert result.data.empty
        assert result.notes[0].code == NO_DATA_CODE


@pytest.mark.parametrize("frequency", ["5min", "1h", "15min"])
def test_the_regularised_index_has_that_spacing(frequency):
    """The regularised index has that spacing."""
    standard = make_standard([1.0, 2.0, 3.0], step_minutes=60)

    result = build(standard, frequency=frequency)

    gaps = result.data.index.to_series().diff().dropna()
    assert (gaps == pd.Timedelta(frequency)).all()
