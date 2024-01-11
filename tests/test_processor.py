"""Test the processor module."""
from xml.etree import ElementTree

import pandas as pd
import pytest
from annalist.annalist import Annalist
from hilltoppy import Hilltop

from hydrobot import processor, xml_data_structure

ann = Annalist()

SITES = [
    "Slimy Bog at Dirt Road",
    "Mid Stream at Cowtoilet Farm",
    "Mostly Cowpiss River at Greenwash Pastures",
]

MEASUREMENTS = [
    "General Nastiness (out of 10)",
    "Atmospheric Pressure",
    "Number of Actual Whole Turds Floating By (t/s)",
    "Dead Cow Concentration (ppm)",
]


@pytest.fixture(autouse=True)
def _no_requests(monkeypatch):
    """Don't allow requests to make requests."""
    monkeypatch.delattr("requests.sessions.Session.request")


@pytest.fixture()
def mock_site_list():
    """Mock response from SiteList server call method."""
    data = {
        "SiteName": SITES,
    }

    return pd.DataFrame(data)


@pytest.fixture()
def mock_measurement_list():
    """Mock response from MeasurementList server call method."""
    data = {
        "MeasurementName": MEASUREMENTS,
    }

    return pd.DataFrame(data)


@pytest.fixture()
def mock_xml_data():
    """Mock response from get_hilltop_xml server call method."""
    with open("tests/xml_test_data_file.xml") as f:
        xml_string = f.read()

    xml_data_list = xml_data_structure.parse_xml(xml_string)

    first_blob = xml_data_list[0]

    root = ElementTree.Element("Hilltop")
    agency = ElementTree.Element("Agency")
    agency.text = "Horizons"
    root.append(agency)

    root.append(first_blob.to_xml_tree())

    first_blob_string = ElementTree.tostring(root)

    return first_blob_string


def test_processor_init(
    capsys, monkeypatch, mock_site_list, mock_measurement_list, mock_xml_data
):
    """Test the processor function."""

    def get_mock_site_list(*args, **kwargs):
        return mock_site_list

    def get_mock_measurement_list(*args, **kwargs):
        return mock_measurement_list

    def get_mock_xml_data(*args, **kwargs):
        return mock_xml_data

    ann.configure(stream_format_str="%(function_name)s | %(site)s")

    # Here we patch the Hilltop Class
    monkeypatch.setattr(Hilltop, "get_site_list", get_mock_site_list)
    monkeypatch.setattr(Hilltop, "get_measurement_list", get_mock_measurement_list)

    # However, in this case, we need to patch the INSTANCE as imported in
    # data_acquisition. Not sure if this makes sense to me, but it works.
    monkeypatch.setattr("hydrobot.data_acquisition.get_hilltop_xml", get_mock_xml_data)

    pr = processor.Processor(
        "https://greenwashed.and.pleasant/",
        SITES[1],
        "GreenPasturesAreNaturalAndEcoFriendlyISwear.hts",
        MEASUREMENTS[1],
        "5T",
    )

    captured = capsys.readouterr()
    ann_output = captured.err.split("\n")

    correct = [
        "standard_series | Mid Stream at Cowtoilet Farm",
        "check_series | Mid Stream at Cowtoilet Farm",
        "quality_series | Mid Stream at Cowtoilet Farm",
        "standard_series | Mid Stream at Cowtoilet Farm",
        "check_series | Mid Stream at Cowtoilet Farm",
        "import_range | Mid Stream at Cowtoilet Farm",
        "__init__ | Mid Stream at Cowtoilet Farm",
    ]

    for i, out in enumerate(ann_output[0:-1]):
        assert out == correct[i], f"Failed on log number {i} with output {out}"

    print(pr.standard_series)

    assert isinstance(pr.standard_series, pd.Series)
    assert int(pr.standard_series.loc["2023-01-01 00:00:00"]) == 10
