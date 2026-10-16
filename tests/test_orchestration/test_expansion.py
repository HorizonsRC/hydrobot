"""Tests for expand_layers: turning one batch entry into one run per layer.


BACKGROUND
----------
Some sites measure at several layers (e.g. pH at 500mm, 1000mm and 2000mmm
depth). In a batch config that's ONE entry listing the layers. Hydrobot
processes one site/measurement pair at a time, so before processing, that
entry is expanded into one "run config" per layer, each with its own
measurement names filled in.

The measurement names come from a template in the config, e.g.
``"pH (-{layer} mm)"``: ``{layer}`` is a placeholder that gets replaced with
the layer value for each run.

Vocabulary:
    layers  the list of layers, in the batch entry (plural; input)
    layer   ONE layer value, on each resulting run (singular; output). You may
            also write a single ``layer`` in an entry as a shorthand for a
            list of one.
    entry   a dict from the batch config: "run config" is what comes out

expand_layers is a pure function (dicts in, dicts out, no files or servers),
so these tests just feed it dicts.

"""
import copy

import pytest

from hydrobot.orchestration.expansion import expand_layers


# A typical batch entry for a layered pH site: three layers, plus a template
# saying how each layer's measurement names are built. Most tests below reuse
# it, and it's never modified (one test checks that explicitly).
PH_ENTRY = {
    "site": "Lake Horowhenua at Buoy",
    "data_family": "ph",
    "layers": [500, 1000, 2000],
    "layer_expansion_template": {
        "standard_measurement_name": "pH (-{layer} mm)",
        "check_measurement_name": "pH Check (-{layer} mm) [pH (-{layer} mm)]",
    },
}


def test_one_run_per_layer():
    # Three layers in, three runs out, each carrying its own single "layer".
    runs = expand_layers(PH_ENTRY)
    assert [r["layer"] for r in runs] == [500, 1000, 2000]


def test_names_filled_from_template():
    # The first run (layer 500) should have {layer} replaced by 500 in both
    # measurement names. Note the check name uses {lauer} twice.
    run = expand_layers(PH_ENTRY)[0]
    assert run["standard_measurement_name"] == "pH (-500 mm)"
    assert run["check_measurement_name"] == "pH Check (-500 mm) [pH (-500 mm)]"

def test_shared_fields_carried_over():
    # Everything in the entry that ISN'T about layers (site, data family,
    # and so on) must be copied into every run unchanged.
    for run in expand_layers(PH_ENTRY):
        assert run["site"] == "Lake Horowhenua at Buoy"
        assert run["data_family"] == "ph"

def test_expansion_keys_removed_from_runs():
    # "layers" and the template only exist to drive expansion. A finished run
    # config shouldn't carry them around (it has its own single "layer").
    for run in expand_layers(PH_ENTRY):
        assert "layers" not in run
        assert "layer_expansion_template" not in run

def test_input_not_mutated():
    # The function must not alter the entry you give it; otherwise expanding
    # twice (or reusing the batch config) would give different answers.
    # Take a copy before, call the funcion, and check nothing changed.
    before = copy.deepcopy(PH_ENTRY)
    expand_layers(PH_ENTRY)
    assert PH_ENTRY == before

def test_runs_are_independent():
    # Add a nested setting to the entry, expand it, then edit it inside the
    # FIRST run. If the runs share one object, the second run would change
    # too. They must not: run configs get edited separately later (e.g. when
    # a user tweaks one layer and reprocesses).
    runs = expand_layers({**PH_ENTRY, "inspection_expiry": {500: {"months": 2}}})
    runs[0]["inspection_expiry"][500]["months"] = 99
    assert runs[1]["inspection_expiry"][500]["months"] == 2

def test_single_layer_goes_through_same_path():
    # An entry with one "layer" (singular) instead of a "layers" list is just
    # shorthand for a list of one: one run, template applied as usual.
    entry = {
        "site": "S",
        "layer": 500,
        "layer_expansion_template": {"standard_measurement_name": "pH (-{layer} mm)"},
    }

    runs = expand_layers(entry)
    assert len(runs) ==  1
    assert runs[0]["standard_measurement_name"] == "pH (-500 mm)"

def test_no_layers_passes_through_unchanged():
    # Most sites aren't layered. With no layers at all, the entry comes back
    # as a single run, exactly as it went in (a list of one entry).
    entry = {"site": "S", "standard_measurement_name": "Rainfall"}
    assert expand_layers(entry) == [entry]

def test_template_can_reference_other_fields():
    # Templates aren't limited to {layer}: any field of the entry works, here
    # {site}. So "S @ 1" is the site name, then the layer.
    entry = {
        "site": "S",
        "layers": [1],
        "layer_expansion_template": {"label": "{site} @ {layer}"},
    }
    assert expand_layers(entry)[0]["label"] == "S @ 1"

def test_unknown_field_in_template_gives_clear_error():
    # A typo'd placeholder ({nope} isn't a field of the entry) should fail
    # with an error naming it, not a mysterious crash somewhere later.
    entry = {
        "layers": [1],
        "layer_expansion_template": {"standard_measurement_name": "{nope} {layer}"},
    }
    with pytest.raises(KeyError, match="nope"):
        expand_layers(entry)

def test_layers_and_layer_together_is_an_error():
    # Giving both the list and the single value is ambiguous (which wins?),
    # so refuse rather than guess.
    with pytest.raises(ValueError, match="both"):
        expand_layers({"layers": [1, 2], "layer": 1})

def test_layers_of_one_matches_single_layer():
    # The two spellings, "layers": [500] and "layer": 500, must give
    # identical results. This pins down the "shorthand for a list of one" idea.
    tmpl = {"standard_measurement_name": "pH (-{layer} mm)"}
    a = expand_layers({"layers": [500], "layer_expansion_template": tmpl})
    b = expand_layers({"layer": 500, "layer_expansion_template": tmpl})
    assert a == b
