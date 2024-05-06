"""Test the XML data structure module."""

from xml.etree import ElementTree

import pandas as pd
import pytest
from defusedxml import ElementTree as DefusedElementTree

from hydrobot import data_structure


@pytest.fixture()
def correct_blobs():
    """
    PyTest fixture providing a list of correct DataSourceBlob dictionaries for testing.

    Returns
    -------
    list
        A list of dictionaries representing correct DataSourceBlob instances.

    Notes
    -----
    This fixture is intended for use in combination with sample_data_source_xml_file.
    If the xml file is parsed correctly, it should contain the same data as in these
    fields.

    Example Usage
    -------------
    def test_xml_parsing_function(sample_data_source_xml_file, correct_blobs)
        # Ensure the XML parsing function correctly handles the provided XML file.
        with open(sample_data_source_xml_file) as f:
            sample_data_source_xml = f.read()
        result = example_xml_function(sample_data_source_xml)
        assert result[0].site_name == correct_blobs[0]["site_name"]
    """
    sitename = "Mid Stream at Cowtoilet Farm"
    datasources = [
        "General Nastiness",
        "Number of Actual Whole Human Turds Floating By",
        "Dead Cow Concentration",
    ]

    tstypes = [
        "StdSeries",
        "StdQualSeries",
        "CheckSeries",
    ]

    data_types = [
        pd.DataFrame,
        pd.DataFrame,
        pd.DataFrame,
    ]

    blob_list = []
    for ds in datasources:
        for ts, dt in zip(tstypes, data_types, strict=True):
            blob = {
                "site_name": sitename,
                "data_source_name": ds,
                "ts_type": ts,
                "data_type": dt,
            }
            blob_list.append(blob)

    return blob_list


def test_parse_xml_file_object(sample_data_source_xml_file, correct_blobs):
    """
    Test the parse_xml function with an XML file object.

    Parameters
    ----------
    sample_data_source_xml_file : pytest fixture
        The path to a sample XML file for testing.
    correct_blobs : pytest fixture
        A list of correct DataSourceBlob dictionaries for comparison.

    Notes
    -----
    This test function checks the behavior of the parse_xml function when provided
    with an open file object representing an XML file. It compares the parsed
    DataSourceBlob instances with a list of correct configurations.

    Assertions
    ----------
    - For each parsed DataSourceBlob instance, assert that the 'site_name' matches
      the corresponding value in the correct_blobs list.
    - For each parsed DataSourceBlob instance, assert that the 'data_source.name'
      matches the corresponding value in the correct_blobs list.
    - For each parsed DataSourceBlob instance, assert that the 'data_source.ts_type'
      matches the corresponding value in the correct_blobs list.
    """
    with open(sample_data_source_xml_file) as f:
        sample_data_source_xml = f

        blob_list = data_structure.parse_xml(sample_data_source_xml)

        for i, blob in enumerate(blob_list):
            assert blob.site_name == correct_blobs[i]["site_name"]
            assert blob.data_source.name == correct_blobs[i]["data_source_name"]
            assert blob.data_source.ts_type == correct_blobs[i]["ts_type"]
            assert isinstance(blob.data.timeseries, correct_blobs[i]["data_type"])


def test_parse_xml_string(sample_data_source_xml_file, correct_blobs):
    """
    Test the parse_xml function with an XML string.

    Parameters
    ----------
    sample_data_source_xml_file : pytest fixture
        The path to a sample XML file for testing.
    correct_blobs : pytest fixture
        A list of correct DataSourceBlob dictionaries for comparison.

    Notes
    -----
    This test function checks the behavior of the parse_xml function when provided
    with an XML string. It compares the parsed DataSourceBlob instances with a list
    of correct configurations.

    Assertions
    ----------
    - For each parsed DataSourceBlob instance, assert that the 'site_name' matches
      the corresponding value in the correct_blobs list.
    - For each parsed DataSourceBlob instance, assert that the 'data_source.name'
      matches the corresponding value in the correct_blobs list.
    - For each parsed DataSourceBlob instance, assert that the 'data_source.ts_type'
      matches the corresponding value in the correct_blobs list.
    """
    with open(sample_data_source_xml_file) as f:
        sample_data_source_xml = f.read()

    blob_list = data_structure.parse_xml(sample_data_source_xml)

    for i, blob in enumerate(blob_list):
        assert blob.site_name == correct_blobs[i]["site_name"]
        assert blob.data_source.name == correct_blobs[i]["data_source_name"]
        assert blob.data_source.ts_type == correct_blobs[i]["ts_type"]
        assert isinstance(blob.data.timeseries, correct_blobs[i]["data_type"])


def test_parse_xml_bytes(sample_data_source_xml_file, correct_blobs):
    """
    Test the parse_xml function with XML content provided as bytes.

    Parameters
    ----------
    sample_data_source_xml_file : pytest fixture
        The path to a sample XML file for testing.
    correct_blobs : pytest fixture
        A list of correct DataSourceBlob dictionaries for comparison.

    Notes
    -----
    This test function checks the behavior of the parse_xml function when provided
    with XML content read as bytes. It compares the parsed DataSourceBlob instances
    with a list of correct configurations.

    Assertions
    ----------
    - For each parsed DataSourceBlob instance, assert that the 'site_name' matches
      the corresponding value in the correct_blobs list.
    - For each parsed DataSourceBlob instance, assert that the 'data_source.name'
      matches the corresponding value in the correct_blobs list.
    - For each parsed DataSourceBlob instance, assert that the 'data_source.ts_type'
      matches the corresponding value in the correct_blobs list.
    """
    with open(sample_data_source_xml_file, "rb") as f:
        sample_data_source_xml = f.read()

    blob_list = data_structure.parse_xml(sample_data_source_xml)

    for i, blob in enumerate(blob_list):
        assert blob.site_name == correct_blobs[i]["site_name"]
        assert blob.data_source.name == correct_blobs[i]["data_source_name"]
        assert blob.data_source.ts_type == correct_blobs[i]["ts_type"]
        assert isinstance(blob.data.timeseries, correct_blobs[i]["data_type"])


def test_parse_xml_etree(sample_data_source_xml_file, correct_blobs):
    """
    Test the parse_xml function with an XML ElementTree object.

    Parameters
    ----------
    sample_data_source_xml_file : pytest fixture
        The path to a sample XML file for testing.
    correct_blobs : pytest fixture
        A list of correct DataSourceBlob dictionaries for comparison.

    Notes
    -----
    This test function checks the behavior of the parse_xml function when provided
    with an XML ElementTree object. It compares the parsed DataSourceBlob instances
    with a list of correct configurations.

    Assertions
    ----------
    - For each parsed DataSourceBlob instance, assert that the 'site_name' matches
      the corresponding value in the correct_blobs list.
    - For each parsed DataSourceBlob instance, assert that the 'data_source.name'
      matches the corresponding value in the correct_blobs list.
    - For each parsed DataSourceBlob instance, assert that the 'data_source.ts_type'
      matches the corresponding value in the correct_blobs list.
    """
    with open(sample_data_source_xml_file) as f:
        xml_string = f.read()
        sample_data_source_xml = DefusedElementTree.fromstring(xml_string)

    blob_list = data_structure.parse_xml(sample_data_source_xml)

    for i, blob in enumerate(blob_list):
        assert blob.site_name == correct_blobs[i]["site_name"]
        assert blob.data_source.name == correct_blobs[i]["data_source_name"]
        assert blob.data_source.ts_type == correct_blobs[i]["ts_type"]
        assert isinstance(blob.data.timeseries, correct_blobs[i]["data_type"])


def test_data_source_to_xml_tree(tmp_path, sample_data_source_xml_file):
    """
    Test the to_xml_tree method of DataSourceBlob for generating correct XML output.

    Parameters
    ----------
    tmp_path : pytest fixture
        A fixture providing a temporary directory path for storing the test output.
    sample_data_source_xml_file : pytest fixture
        The path to a sample XML file for testing.

    Notes
    -----
    This test function checks the correctness of the to_xml_tree method of
    DataSourceBlob when generating XML output. It compares the generated XML with the
    expected XML from the sample data source XML file. Before comparison, the xml from
    both sources are canonicalized (reformatted into a standardized format),
    and whitespace is removed.

    Assertions
    ----------
    - Assert that the canonicalized content of the generated XML matches the
        canonicalized content of the expected XML from the sample data source XML file.
    """
    with open(sample_data_source_xml_file) as f:
        sample_data_source_xml = f.read()

    blob_list = data_structure.parse_xml(sample_data_source_xml)

    output_path = tmp_path / "output.xml"
    # output_path = "output.xml"
    data_structure.write_hilltop_xml(blob_list, output_path)

    with open(output_path) as f:
        output_xml = f.read()

    assert ElementTree.canonicalize(
        sample_data_source_xml,
        strip_text=True,
    ) == ElementTree.canonicalize(
        output_xml,
        strip_text=True,
    )
