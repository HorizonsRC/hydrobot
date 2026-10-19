"""Tests for fill_run_config and resolve.

BACKGROUND
----------
Before a run can be processed, its config needs completing: a missing
``to_date`` defaults to "now", and missing ``from_date`` is worked out by
asking the provider where processing last got to. ``fill_run_config`` does
that for one run; ``resolve`` does expansion (one entry -> one run per layer)
and then fills each run.

HOW THESE TESTS WORK
--------------------
The provider normally talks to a server. Here a FakeProvider is given a table
of canned answers ("for this site and measurement, last processed time is X"),
so no server is involved. It also records every question it was asked, so
tests can check that the code asked the RIGHT question (or, sometimes,
asked nothing at all).

A fixed ``NOW`` is passed in instead of reading the real clock, so the
expected dates are always the same.

"""

from datetime import datetime

import pytest

from hydrobot.orchestration.resolve import fill_run_config, resolve
from hydrobot.providers.types import DataProviderError, SiteInfo

# The "current time" for every test. Fixed so expected values never change.
NOW = datetime(2026, 10, 19, 9, 30)

# A time the fake archive will report as "processing got this far".
LAST_RUN = datetime(2025, 10, 22, 11, 0)


class FakeProvider:
    """A stand-in provider that answers last_processed_time from a table.

    ``answers`` maps (site, measurement) to the datetime (or None) to return.
    Asking about anything NOT in the table raises KeyError, so a test fails
    loudly if the code asks about the wrong site or measurement name.
    ``self.calls`` records each question asked, in order.
    """

    def __init__(self, answers, site_codes=None):
        self.answers = answers
        self.site_codes = site_codes or {}
        self.calls = []  # last_processed_time questions: (site, measurement)
        self.site_calls = []  # get_site_info questions: site

    def last_processed_time(self, site, measurement):
        self.calls.append((site, measurement))
        return self.answers[(site, measurement)]

    def get_site_info(self, site):
        self.site_calls.append(site)
        return SiteInfo(code=self.site_codes[site])


class FailingProvider:
    """A provider whose lookup always breaks, as if the server were down."""

    def last_processed_time(self, site, measurement):
        raise DataProviderError("archive unreachable")

    def get_site_info(self, site):
        raise DataProviderError("archive uncreachable")


def make_run(**overrides):
    """A minimal run config; keyword arguments add or replace fields."""
    run = {
        "site": "Site A",
        "site_code": "SA",
        "standard_measurement_name": "Rainfall"
    }
    run.update(overrides)
    return run


# --- fill_run_config: to_date ------------------------------------------------


def test_missing_to_date_defaults_to_now():
    # Neither date given, but the provider knows from_date. to_date should be
    # the current time, written to the minute.
    provider = FakeProvider({("Site A", "Rainfall"): LAST_RUN})
    filled = fill_run_config(make_run(), provider, now=NOW)
    assert filled["to_date"] == "2026-10-19 09:30"


def test_explicit_to_date_is_kept():
    # A to_date the user chose must never be replaced by "now".
    provider = FakeProvider({("Site A", "Rainfall"): LAST_RUN})
    filled = fill_run_config(
        make_run(to_date="2025-12-31 00:00"), provider, now=NOW
    )
    assert filled["to_date"] == "2025-12-31 00:00"


def test_to_date_of_none_counts_as_missing():
    # A blank value in the YAML (``to_date:`` with nothing after it) loads as
    # None. That should be treated the same as not being there at all.
    provider = FakeProvider({("Site A", "Rainfall"): LAST_RUN})
    filled = fill_run_config(make_run(to_date=None), provider, now=NOW)
    assert filled["to_date"] == "2026-10-19 09:30"


# --- fill_run_config: from_date ----------------------------------------------


def test_missing_from_date_comes_from_provider():
    # The provider says processing got to 22 Oct 2025 11:00, so that's where
    # the next run starts. It should be asked about this run's site and its
    # standard measurement name.
    provider=FakeProvider({("Site A", "Rainfall"): LAST_RUN})
    filled = fill_run_config(make_run(), provider, now=NOW)
    assert filled["from_date"] == "2025-10-22 11:00"
    assert provider.calls == [("Site A", "Rainfall")]


def test_explicit_from_date_is_kept_and_provider_not_asked():
    # If from_date is already set, there's nothing to work out. Importantly
    # the provider must not be called at all: the fake has no answers, so any
    # call would raise KeyError. (This is also how a user's edited run config
    # gets reprocessed without being second-guessed.)
    provider = FakeProvider({})
    filled = fill_run_config(
        make_run(from_date="2025-01-01 00:00"), provider, now=NOW
    )
    assert filled["from_date"] == "2025-01-01 00:00"
    assert provider.calls == []


def test_archive_measurement_name_preferred_when_given():
    # The archive sometimes calls a measurement something different. When the
    # run says so, the archive lookup uses that name, not the live one.
    provider = FakeProvider({("Site A", "Rainfall (Archive)"): LAST_RUN})
    run = make_run(archive_standard_measurement_name="Rainfall (Archive)")
    filled = fill_run_config(run, provider, now=NOW)
    assert filled["from_date"] == "2025-10-22 11:00"
    assert provider.calls == [("Site A", "Rainfall (Archive)")]


def test_archive_measurement_name_of_none_falls_back_to_standard():
    # A blank archive name in the YAML (None) means "same as the live name".
    provider = FakeProvider({("Site A", "Rainfall"): LAST_RUN})
    run = make_run(archive_standard_measurement_name=None)
    fill_run_config(run, provider, now=NOW)
    assert provider.calls == [("Site A", "Rainfall")]


def test_seconds_are_dropped_from_from_date():
    # Dates are written to the minute, so 11:0035 becomes 11:00. That
    # restarts a few seconds early rather than late, which is the safe
    # direction (it can only reprocess a little, never skip data).
    provider = FakeProvider(
        {("Site A", "Rainfall"): datetime(2025, 10, 22, 11, 0, 35)}
    )
    filled = fill_run_config(make_run(), provider, now=NOW)
    assert filled["from_date"] == "2025-10-22 11:00"


# --- fill_run_config: failure modes ------------------------------------------


def test_never_archived_and_no_from_date_is_a_clear_error():
    # The provider reports None: nothing has ever been processed here. A
    # brand-new site genuinely needs a human-supplied start date, so say so,
    # naming the site and measurement so the right config line gets fixed.
    provider = FakeProvider({("Site A", "Rainfall"): None})
    with pytest.raises(ValueError, match="Site A.*Rainfall.*from_date"):
        fill_run_config(make_run(), provider, now=NOW)


def test_never_archived_error_points_at_archive_settings():
    # An empty archive can mean "new site" OR "wrong archive name" (the server
    # just returns nothing either way). We refuse to guess a start date, since
    # wrongly reprocessing a whole history is far costlier than one config
    # line. So the message must name the archive settings to check.
    provider = FakeProvider({("Site A", "Rainfall"): None})
    with pytest.raises(ValueError, match="archive_standard_measurement_name"):
        fill_run_config(make_run(), provider, now=NOW)


def test_provider_errors_are_now_swallowed():
    # If the archive can't be reached, that must surface as an error, not be
    # quietly ignored (the old code only printed a warning and carried on).
    with pytest.raises(DataProviderError, match="unreachable"):
        fill_run_config(make_run(), FailingProvider(), now=NOW)


def test_input_not_mutated():
    # The run config you pass in must be left exactly as it was; thefilled
    # version is a separate copy.
    provider = FakeProvider({("Site A", "Rainfall"): LAST_RUN})
    run = make_run()
    before = dict(run)
    fill_run_config(run, provider, now=NOW)
    assert run == before


# --- resolve: expansion + filling together -----------------------------------


def test_resolve_fills_each_layer_using_its_own_measurement_name():
    # One entry with two layers expands to two runs. Each run's from_date
    # lookup must use THAT layer's expanded name. The fake only knows the two
    # correct questions, so asking about an unexpected name would fail.
    entry = {
        "site": "Lake",
        "site_code": "LK",
        "layers": [500, 1000],
        "layer_expansion_template": {"standard_measurement_name": "pH (-{layer} mm)"},
    }
    provider = FakeProvider(
        {
            ("Lake", "pH (-500 mm)"): datetime(2025, 1, 1, 0, 0),
            ("Lake", "pH (-1000 mm)"): datetime(2025, 2, 2, 0, 0),
        }
    )

    runs = resolve(entry, provider, now=NOW)

    assert [r["layer"] for r in runs] == [500, 1000]
    assert [r["from_date"] for r in runs] == ["2025-01-01 00:00", "2025-02-02 00:00"]
    assert all(r["to_date"] == "2026-10-19 09:30" for r in runs)


def test_resolve_entry_without_layers_gives_one_run():
    # Most sites aren't layered: one entry, one run, still filled in.
    provider = FakeProvider({("Site A", "Rainfall"): LAST_RUN})
    runs = resolve(make_run(), provider, now=NOW)
    assert len(runs) == 1
    assert runs[0]["from_date"] == "2025-10-22 11:00"


def test_resolve_with_from_date_given_never_asks_the_provider():
    # A batch entry with an explicit from_date and several layers shares that
    # date across all runs and needs no archive lookups at all.
    entry = {
        "site": "Lake",
        "site_code": "LK",
        "from_date": "2025-06-01 00:00",
        "layers": [500, 1000],
        "layer_expansion_template": {"standard_measurement_name": "pH (-{layer} mm)"},
    }
    provider = FakeProvider({})  # any question would raise KeyError
    runs = resolve(entry, provider, now=NOW)
    assert[r["from_date"] for r in runs] == ["2025-06-01 00:00"] * 2
    assert provider.calls == []


def test_resolve_gives_every_layer_the_site_code():
    # Layers belong to one site, so each run ends up with the same site_code
    # (looked up per run here, the fake would raise if asked about any other
    # site).
    entry = {
        "site": "Lake",
        "from_date": "2025-06-01 00:00",
        "layers": [500, 1000],
        "layer_expansion_template": {"standard_measurement_name": "pH (-{layer} mm)"},
    }
    provider = FakeProvider({}, site_codes={"Lake": "LK"})
    runs = resolve(entry, provider, now=NOW)
    assert [r["site_code"] for r in runs] == ["LK", "LK"]
