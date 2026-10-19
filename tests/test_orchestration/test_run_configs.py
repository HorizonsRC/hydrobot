"""Tests for saving and loading run configs (the setup step's output).

BACKGROUND
----------
Setup turns a batch entry into one saved config file per run, in that run's
own folder. After that the file belongs to the analyst, who may edit it and
reprocess from it. So the important behaviours are about SAFETY:

*   a file is written once and never overwritten (it may hold edits),
*   setup is all-or-nothing per entry (no half-written batches),
*   values that YAML could misread (dates, versions) are always quoted,
*   what you load is exactly the run that was resolved.

HOW THESE TESTS WORK
--------------------
``tmp_path`` is a fresh, empty temporary folder that pytest provides for each
test, so the tests write real files without touching anything real. The
provider is a FakeProvider with canned answers, as in test_resolve.py.
"""

from datetime import datetime

import pytest
import yaml

from hydrobot.orchestration import run_configs
from hydrobot.orchestration.resolve import resolve
from hydrobot.orchestration.run_configs import (
    config_document,
    config_path,
    load_run_config,
    package_versions,
    setup_entry,
    write_run_config,
)

from hydrobot.providers.types import SiteInfo

NOW = datetime(2026, 10, 19, 9, 30)
VERSIONS = {"hydrobot": "0.9.15", "whurl": "0.1.3"}
BATCH_CONFIG = "503_PH_batch_config.yaml"


class FakeProvider:
    """Canned answers for the two questions resolving asks a provider.

    ``last_run`` maps measurement name -> when processing last got to
    (or None for "never archived"). Every site's code is "LHB".
    """

    def __init__(self, last_run):
        self.last_run = last_run

    def last_processed_time(self, site, measurement):
        return self.last_run[measurement]

    def get_site_info(self, site):
        return SiteInfo(code="LHB")


def make_entry(**overrides):
    """A batch entry for a two-layer pH site; kwargs add or replace fields."""
    entry = {
        "batch": 503,
        "measurement_folder": "pH",
        "data_source_code": "PH",
        "site": "Lake Horowhenua at Buoy",
        "data_family": "ph",
        "frequency": "5min",
        "layers": [500, 1000],
        "layer_expansion_template": {
            "standard_measurement_name": "pH (-{layer} mm)",
            "layer_label": "-{layer}mm",
        },
    }

    entry.update(overrides)
    return entry


def provider_knowing_both_layers():
    return FakeProvider(
        {
            "pH (-500 mm)": datetime(2026, 9, 30, 11, 0),
            "pH (-1000 mm)": datetime(2026, 9, 29, 8, 0),
        }
    )


def setup(tmp_path, entry=None, provider=None):
    """Run setup_entry with the standard fixed inputs."""
    return setup_entry(
        tmp_path,
        entry or make_entry(),
        provider or provider_knowing_both_layers(),
        now=NOW,
        batch_config=BATCH_CONFIG,
        versions=VERSIONS,
    )


# --- Where files go, and what's in them --------------------------------------


def test_one_file_per_layer_in_the_conversation_place(tmp_path):
    # Two layers -> two files, each in its own layer folder, named by the
    # convention from paths.py (batch_source_sitecode_layer_purpose).
    paths = setup(tmp_path)
    site_dir = tmp_path / "pH" / "503" / "Lake Horowhenua at Buoy"
    assert paths == [
        site_dir / "-500mm" / "503_PH_LHB_-500mm_config.yaml",
        site_dir / "-1000mm" / "503_PH_LHB_-1000mm_config.yaml",
    ]
    assert all(p.exists() for p in paths)


def test_header_records_how_the_file_was_made(tmp_path):
    # Read the raw file (not through load_run_config, which hides the header)
    # and check the setup block.
    path = setup(tmp_path)[0]
    header = yaml.safe_load(path.read_text())["setup"]
    assert header["hydrobot_version"] == "0.9.15"
    assert header["whurl_version"] == "0.1.3"
    assert header["set_up_at"] == "2026-10-19 09:30"
    assert header["batch_config"] == BATCH_CONFIG


def test_header_lists_exactly_the_values_hydrobot_filled(tmp_path):
    # The entry supplied batch, site, data_family and so on. Hydrobot worked
    # out the layer, the names built from the template, the site code and
    # both dates, and only THOSE are listed.
    path = setup(tmp_path)[0]
    header = yaml.safe_load(path.read_text())["setup"]
    assert header["filled_by_hydrobot"] == [
        "from_date", "layer", "layer_label",
        "site_code", "standard_measurement_name", "to_date",
    ]


def test_values_the_user_supplied_are_not_listed_as_filled(tmp_path):
    # If the user gave from_date and site_code themselves, those aren't
    # hydrobot's doing, so they must not appear in the filled list.
    entry = make_entry(from_date="2026-01-01 00:00", site_code="LHB")
    path = setup(tmp_path, entry, FakeProvider({}))[0]
    filled = yaml.safe_load(path.read_text())["setup"]["filled_by_hydrobot"]
    assert "from_date" not in filled and "site_code" not in filled


def test_keys_are_in_reading_order(tmp_path):
    # Identity keys first, dates last, so the file reads naturally.
    path = setup(tmp_path)[0]
    keys = list(yaml.safe_load(path.read_text()))
    assert keys[0] == "setup"
    assert keys[1:6] == ["batch", "measurement_folder", "data_source_code", "site", "site_code"]
    assert keys[-2:] == ["from_date", "to_date"]


def test_a_run_may_not_have_its_own_setup_key():
    # "setup" is reserved for the header; refuse rather than silently clash.
    with pytest.raises(ValueError, match="setup"):
        config_document({}, {"setup": 1}, now=NOW, batch_config="b", versions=VERSIONS)


# ---------------------------------------------------------------------------
# Quoting: values YAML could misread
# ---------------------------------------------------------------------------


def test_dates_and_labels_are_written_in_double_quotes(tmp_path):
    # Look at the raw text. Quoting is what stops "2026-10-19 09:30:15" (if an
    # analyst adds seconds) or "-500mm" from being read as something else.
    text = setup(tmp_path)[0].read_text()
    assert 'from_date: "2026-09-30 11:00"' in text
    assert 'to_date: "2026-10-19 09:30"' in text
    assert 'layer_label: "-500mm"' in text


def test_a_version_that_looks_like_a_number_stays_text(tmp_path):
    # "0.9" unquoted would load as the number 0.9. Versions are always quoted.
    path = setup_entry(
        tmp_path, make_entry(), provider_knowing_both_layers(),
        now=NOW, batch_config=BATCH_CONFIG,
        versions={"hydrobot": "0.9", "whurl": "1.10"},
    )[0]
    header = yaml.safe_load(path.read_text())["setup"]
    assert header["hydrobot_version"] == "0.9"
    assert header["whurl_version"] == "1.10"


def test_other_misreadable_strings_are_quoted_automatically(tmp_path):
    # A string that would change meaning if written plain (here "yes", which
    # YAML reads as true) must come back as the same string.
    entry = make_entry(note="yes")
    path = setup(tmp_path, entry)[0]
    assert yaml.safe_load(path.read_text())["note"] == "yes"


# ---------------------------------------------------------------------------
# Round trip
# ---------------------------------------------------------------------------


def test_loading_gives_back_exactly_the_resolved_run(tmp_path):
    # What setup saved, load_run_config returns: the run config WITHOUT the
    # header. Compared against resolve()'s direct output for the same inputs.
    entry = make_entry()
    expected = resolve(entry, provider_knowing_both_layers(), now=NOW)
    paths = setup(tmp_path, entry)
    assert [load_run_config(p) for p in paths] == expected


def test_dates_edited_with_seconds_and_no_quotes_still_load_as_text(tmp_path):
    # An analyst types a date with seconds and leaves off the quotes. YAML then
    # produces a datetime object. Loading converts it back to our standard
    # text so nothing downstream ever has to cope with datetimes.
    path = setup(tmp_path)[0]
    edited = path.read_text().replace(
        'from_date: "2026-09-30 11:00"', "from_date: 2026-09-30 11:00:30"
    )
    path.write_text(edited)
    assert load_run_config(path)["from_date"] == "2026-09-30 11:00"


# ---------------------------------------------------------------------------
# Safety: never overwrite, all or nothing
# ---------------------------------------------------------------------------


def test_never_overwrites_an_existing_config(tmp_path):
    # An analyst has edited the first layer's config. Running setup again must
    # refuse, and must leave their file byte-for-byte alone.
    first = setup(tmp_path)[0]
    first.write_text("analyst's careful edits\n")
    with pytest.raises(FileExistsError, match="already exist"):
        setup(tmp_path)
    assert first.read_text() == "analyst's careful edits\n"


def test_write_run_config_itself_refuses_to_overwrite(tmp_path):
    # The same protection at the lowest level, in case something calls the
    # writer directly instead of going through setup_entry.
    run = resolve(make_entry(), provider_knowing_both_layers(), now=NOW)[0]
    doc = config_document(make_entry(), run, now=NOW, batch_config="b", versions=VERSIONS)
    write_run_config(tmp_path, run, doc)
    with pytest.raises(FileExistsError, match="analyst"):
        write_run_config(tmp_path, run, doc)


def test_nothing_is_written_if_any_layer_already_exists(tmp_path):
    # Only the SECOND layer's config exists already. Setup must not write the
    # first layer's file and then trip over the second: it should check all
    # of them first and write none.
    runs = resolve(make_entry(), provider_knowing_both_layers(), now=NOW)
    second = config_path(tmp_path, runs[1])
    second.parent.mkdir(parents=True)
    second.write_text("existing")

    with pytest.raises(FileExistsError):
        setup(tmp_path)

    assert not config_path(tmp_path, runs[0]).exists()


def test_nothing_is_written_if_a_later_layer_cannot_be_resolved(tmp_path):
    # The archive has never seen the second layer and the entry gives no
    # from_date, so resolving the second layer fails. The first layer was
    # fine, but no file at all should be left behind.
    provider = FakeProvider(
        {"pH (-500 mm)": datetime(2026, 9, 30, 11, 0), "pH (-1000 mm)": None}
    )
    with pytest.raises(ValueError, match="from_date"):
        setup(tmp_path, provider=provider)
    assert list(tmp_path.rglob("*.yaml")) == []


# ---------------------------------------------------------------------------
# Versions
# ---------------------------------------------------------------------------


def test_package_versions_reports_both_packages():
    versions = package_versions()
    assert set(versions) == {"hydrobot", "whurl"}
    assert all(isinstance(v, str) for v in versions.values())


def test_package_versions_falls_back_when_not_installed(monkeypatch):
    # Running from a source checkout, a package may have no installed version.
    # That shouldn't crash setup; it records "unknown".
    def not_installed(name):
        raise run_configs.md.PackageNotFoundError(name)

    monkeypatch.setattr(run_configs.md, "version", not_installed)
    assert package_versions() == {"hydrobot": "unknown", "whurl": "unknown"}


