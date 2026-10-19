"""Tests for run_dir and run_filename: where a run's files live and their names.

BACKGROUND
----------
Every processing run (one site, one measurement, maybe one layer) gets its own
folder and a set of files named by a fixed convention, e.g.

    Dissolved Oxygen/500/Manawatu at Teachers College/500_DO_TCO_config.yaml

Layered sites get one extra folder level for the layer, and the layer label
joins the file names, e.g. ``Water Temperature/503/Lake Horowhenua at Buoy/
-500mm/503_WT_LHB_-500mm_config.yaml``.

These functions only build paths and names from a run config; they never touch
the disk, so the tests need no real folders.
"""

from pathlib import Path

import pytest

from hydrobot.orchestration.paths import run_dir, run_filename

ROOT = Path("hydrobot_root")


def make_run(**overrides):
    """An unlayered run config with every key paths need; kwargs override."""
    run = {
        "batch": 500,
        "measurement_folder": "Dissolved Oxygen",
        "data_source_code": "DO",
        "site": "Manawatu at Teachers College",
        "site_code": "TCO",
    }
    run.update(overrides)
    return run


def make_layered_run(**overrides):
    """The same, but for a layered site (note the layer_label)."""
    return make_run(
        batch=503,
        measurement_folder="Water Temperature",
        data_source_code="WT",
site="Lake Horowhenua at Buoy",
        site_code="LHB",
        layer_label="-500mm",
        **overrides,
    )


# --- run_dir -----------------------------------------------------------------


def test_unlayered_run_dir():
    # root / measurement / batch / site, and nothing more.
    assert run_dir(ROOT, make_run()) == (
        ROOT / "Dissolved Oxygen" / "500" / "Manawatu at Teachers College"
    )


def test_layered_run_dir_has_an_extra_level():
    # A layer_lavel adds one more folder below the site.
    assert run_dir(ROOT, make_layered_run()) == (
        ROOT / "Water Temperature" / "503" / "Lake Horowhenua at Buoy" / "-500mm"
    )


def test_layer_label_of_none_means_unlayered():
    # A blank layer_label (None, as from an empty YAML value), must behave like
    # no layer at all, not create a folder called "None".
    assert run_dir(ROOT, make_run(layer_label=None)) == run_dir(ROOT, make_run())


def test_root_can_be_given_as_text():
    # Callers may pass a plain string (e.g. a network path from a setting).
    assert run_dir("some/root", make_run()) == Path("some/root") / "Dissolved Oxygen" / "500" / "Manawatu at Teachers College"


# --- run_filename ------------------------------------------------------------

def test_unlayered_filename():
    # <batch>_<source>_<site_code>_<purpose>.<extension>
    assert run_filename(make_run(), "config", "yaml") == "500_DO_TCO_config.yaml"


def test_layered_filename_includes_the_layer_label():
    # The layer label sits between the site code and the purpose.
    assert (
        run_filename(make_layered_run(), "config", "yaml")
        == "503_WT_LHB_-500mm_config.yaml"
    )

def test_other_purposes_and_extensions():
    # The same function names every file in the run folder.
    assert run_filename(make_run(), "script", "py") == "500_DO_TCO_script.py"
    assert run_filename(make_run(), "data", "xml") == "500_DO_TCO_data.xml"


def test_numeric_layer_label_and_batch_are_fine():
    # Batch numbers and labels may arrive as ints; they're written as text.
    run = make_run(batch=501, layer_label=1000)
    assert run_filename(run, "data", "hts") == "501_DO_TCO_1000_data.hts"


# --- Failure modes -----------------------------------------------------------

def test_missing_keys_are_named_in_the_error():
    # An incomplete run config should say exactly which keys are absent.
    run = make_run()
    del run["data_source_code"]
    with pytest.raises(ValueError, match="data_source_code"):
        run_filename(run, "config", "yaml")


def test_missing_site_code_hints_at_the_fill_stage():
    # site_code is the likeliest to be missing (it's filled in from the
    # provider), so the error points at that.
    run = make_run(site_code=None)
    with pytest.raises(ValueError, match="fill stage"):
        run_filename(run, "config", "yaml")


def test_run_dir_needs_its_own_keys():
    # run_dir doesn't need a site_code, but it does need the folder names.
    run = make_run()
    del run["measurement_folder"]
    with pytest.raises(ValueError, match="measurement_folder"):
        run_dir(ROOT, run)


@pytest.mark.parametrize(
    "bad_site",
    [
        "Site/With/Slashes",    # would silently create extra folders
        "Site: Upper",          # ':' isn't allowed in Windows names
        "..",                   # would climb out of the batch folder
        "Site."                 # Windows doesn't allow a trailing dot
        " Padded ",             # leading/trailing spaces cause confusion
        "",                     # nothing to name a folder with
    ],
)
def test_unsafe_site_names_are_refused(bad_site):
    # We refuse rather than quietly "clean" the name: a silently altered site
    # name would give the files a different identity from their config.
    with pytest.raises(ValueError, match="can't be used in a file path"):
        run_dir(ROOT, make_run(site=bad_site))
