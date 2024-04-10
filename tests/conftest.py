"""Fixtures to be shared across many pytests."""
import pytest


@pytest.fixture()
def sample_data_source_xml_file():
    """
    PyTest fixture providing the path to a sample XML file for testing.

    Returns
    -------
    str
        The file path to the sample XML file.

    Notes
    -----
    This fixture is intended to be used in tests that require a sample XML file.
    The XML file contains output from Hilltop. The file contains Standard, Check and
    Quality data for Rainfall and General Nastiness Mid Stream at Cowtoilet Farm.

    Example Usage
    -------------
    def test_xml_parsing_function(sample_data_source_xml_file)
        # Ensure the XML parsing function correctly handles the provided XML file.
        with open(sample_data_source_xml_file) as f:
            sample_data_source_xml = f.read()
        result = example_xml_function(sample_data_source_xml)
        assert result == expected_result
    """
    file_path = "tests/test_data/xml_test_data_file.xml"
    return file_path
