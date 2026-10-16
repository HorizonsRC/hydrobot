import copy

import pytest

from hydrobot.orchestration.expansion import expand_layers

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
    runs = expand_layers(PH_ENTRY)
    assert [r["layer"] for r in runs] == [500, 1000, 2000]


def test_names_filled_from_template():
    run = expand_layers(PH_ENTRY)[0]
    assert run["standard_measurement_name"] == "pH (-500 mm)"
    assert run["check_measurement_name"] == "pH Check (-500 mm) [pH (-500 mm)]"

def test_shared_fields_carried_over():
    for run in expand_layers(PH_ENTRY):
        assert run["site"] == "Lake Horowhenua at Buoy"
        assert run["data_family"] == "ph"

def test_expansion_keys_removed_from_runs():
    for run in expand_layers(PH_ENTRY):
        assert "layers" not in run
        assert "layer_expansion_template" not in run

def test_input_not_mutated():
    before = copy.deepcopy(PH_ENTRY)
    expand_layers(PH_ENTRY)
    assert PH_ENTRY == before

def test_runs_are_independent():
    runs = expand_layers({**PH_ENTRY, "inspection_expiry": {500: {"months": 2}}})
    runs[0]["inspection_expiry"][500]["months"] = 99
    assert runs[1]["inspection_expiry"][500]["months"] == 2

def test_single_layer_goes_through_same_path():
    entry = {
        "site": "S",
        "layer": 500,
        "layer_expansion_template": {"standard_measurement_name": "pH (-{layer} mm)"},
    }

    runs = expand_layers(entry)
    assert len(runs) ==  1
    assert runs[0]["standard_measurement_name"] == "pH (-500 mm)"

def test_no_layers_passes_through_unchanged():
    entry = {"site": "S", "standard_measurement_name": "Rainfall"}
    assert expand_layers(entry) == [entry]

def test_template_can_reference_other_fields():
    entry = {
        "site": "S",
        "layers": [1],
        "layer_expansion_template": {"label": "{site} @ {layer}"},
    }
    assert expand_layers(entry)[0]["label"] == "S @ 1"

def test_unknown_field_in_template_gives_clear_error():
    entry = {
        "layers": [1],
        "layer_expansion_template": {"standard_measurement_name": "{nope} {layer}"},
    }
    with pytest.raises(KeyError, match="nope"):
        expand_layers(entry)

def test_layers_and_layer_together_is_an_error():
    with pytest.raises(ValueError, match="both"):
        expand_layers({"layers": [1, 2], "layer": 1})

def test_layers_of_one_matches_single_layer():
    tmpl = {"standard_measurement_name": "pH (-{layer} mm)"}
    a = expand_layers({"layers": [500], "layer_expansion_template": tmpl})
    b = expand_layers({"layer": 500, "layer_expansion_template": tmpl})
    assert a == b
