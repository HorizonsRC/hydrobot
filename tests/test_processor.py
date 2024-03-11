# pyright: reportUnusedImport=false
"""Test the processor module."""

from xml.etree import ElementTree

import numpy as np
import pandas as pd
import pytest
from annalist.annalist import Annalist
from defusedxml import ElementTree as DefusedElementTree
from hilltoppy import Hilltop

from hydrobot import data_sources, data_structure, processor, utils
from hydrobot.data_sources import QualityCodeEvaluator
from hydrobot.data_structure import parse_xml

ann = Annalist()

SITES = [
    "Slimy Bog at Dirt Road",
    "Mid Stream at Cowtoilet Farm",
    "Mostly Cowpiss River at Greenwash Pastures",
]

MEASUREMENTS = [
    "General Nastiness",
    "Number of Actual Whole Human Turds Floating By",
    "Dead Cow Concentration",
]

CHECK_MEASUREMENTS = [
    "General Nastiness",
    "Turdidity Sensor Reading [Number of Actual Whole Human Turds Floating By]",
    "Dead Cow Concentration",
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
        "MeasurementName": MEASUREMENTS + CHECK_MEASUREMENTS,
    }

    return pd.DataFrame(data)


@pytest.fixture()
def mock_qc_evaluator_dict():
    """Mock response from get_qc_evaluator_dict lookup method."""
    qc_500_limits = [2.5, 5.4, 230]
    qc_600_limits = [4, 0.9, 480]
    config_data = {}
    for i, meas in enumerate(MEASUREMENTS):
        config_data[meas] = QualityCodeEvaluator(
            qc_500_limits[i],
            qc_600_limits[i],
            meas,
        )

    return config_data


@pytest.fixture()
def mock_xml_data():
    """Mock response from get_hilltop_xml server call method."""
    with open("tests/xml_test_data_file.xml") as f:
        xml_string = f.read()

    return xml_string


@pytest.fixture()
def mock_get_data():
    """
    Fixture to mock the response from the get_data server call method.

    Parameters
    ----------
    No direct parameters; indirectly passed into the inner function.

    Notes
    -----
    This fixture simulates the response from the get_data server call method.
    It reads XML test data from the specified file and provides a function that extracts
    relevant data based on input parameters.

    Example Usage
    -------------
    To use this fixture in a test, include it as a parameter in the test function.
    For example:

    ```python
    def test_my_function(mock_get_data):
        # Your test code here
        result = my_function_that_uses_get_data(mock_get_data)
        assert result == expected_result
    ```
    """
    with open("tests/xml_test_data_file.xml") as f:
        xml_string = f.read()

    xml_root = ElementTree.Element(xml_string)

    def _extract_data(
        base_url,
        hts,
        site,
        measurement,
        from_date,
        to_date,
        tstype,
    ):
        _ = base_url, hts, site
        data_blobs = parse_xml(xml_string)

        keep_blobs = []

        type_map = {
            "Standard": "StdSeries",
            "Quality": "StdQualSeries",
            "Check": "CheckSeries",
        }
        if data_blobs is not None:
            for blob in data_blobs:
                if (
                    blob.data_source.name == measurement
                    and blob.data_source.ts_type == type_map[tstype]
                ):
                    conv_timestamps = utils.mowsecs_to_datetime_index(
                        blob.data.timeseries.index
                    )
                    if from_date is None:
                        from_date = conv_timestamps[0]
                    if to_date is None:
                        to_date = conv_timestamps[-1]
                    mask = (conv_timestamps >= pd.to_datetime(from_date)) & (
                        conv_timestamps <= pd.to_datetime(to_date)
                    )
                    blob.data.timeseries = blob.data.timeseries[mask]  # type: ignore
                    keep_blobs += [blob]
        else:
            return None

        return keep_blobs

    return xml_root, _extract_data


def test_processor_init(
    capsys,
    monkeypatch,
    mock_site_list,
    mock_measurement_list,
    mock_xml_data,
    mock_qc_evaluator_dict,
):
    """
    Test the initialization of the Processor class.

    Parameters
    ----------
    capsys : _pytest.capture.CaptureFixture
        pytest fixture to capture stdout and stderr output.
    monkeypatch : _pytest.monkeypatch.MonkeyPatch
        pytest fixture to modify attributes or behavior during testing.
    mock_site_list : Any
        Mocked data for the site list.
    mock_measurement_list : Any
        Mocked data for the measurement list.
    mock_xml_data : Any
        Mocked data for Hilltop XML.
    mock_qc_evaluator_dict : Any
        Mocked data for the QC evaluator dictionary.

    Notes
    -----
    This test function initializes a Processor instance and checks if the attributes
    and initializations are as expected. It also validates the log outputs using
    the captured output from capsys.

    It patches several functions using monkeypatch to provide the necessary mock data.
    The patched functions include Hilltop class methods for site and measurement lists,
    as well as the get_hilltop_xml function from data_acquisition.

    Assertions
    ----------
    - Log outputs are validated to ensure proper initialization and function calls.
    - Attributes of the Processor instance, such as standard_series, are checked.
    - The data in the standard_series is verified for correctness.

    """

    def get_mock_site_list(*args, **kwargs):
        _ = args, kwargs
        return mock_site_list

    def get_mock_measurement_list(*args, **kwargs):
        _ = args, kwargs
        return mock_measurement_list

    def get_mock_xml_data(*args, **kwargs):
        _ = args, kwargs
        return mock_xml_data

    def get_mock_qc_evaluator_dict(*args, **kwargs):
        _ = args, kwargs
        return mock_qc_evaluator_dict

    ann.configure(stream_format_str="%(function_name)s | %(site)s")

    # Here we patch the Hilltop Class
    monkeypatch.setattr(Hilltop, "get_site_list", get_mock_site_list)
    monkeypatch.setattr(Hilltop, "get_measurement_list", get_mock_measurement_list)
    monkeypatch.setattr(
        data_sources,
        "get_qc_evaluator_dict",
        get_mock_qc_evaluator_dict,
    )

    # However, in these cases, we need to patch the INSTANCE as imported in
    # data_acquisition. Not sure if this makes sense to me, but it works.
    monkeypatch.setattr("hydrobot.data_acquisition.get_hilltop_xml", get_mock_xml_data)

    pr = processor.Processor(
        base_url="https://greenwashed.and.pleasant/",
        site=SITES[1],
        standard_hts="GreenPasturesAreNaturalAndEcoFriendlyISwear.hts",
        standard_measurement_name=MEASUREMENTS[1],
        check_measurement_name=CHECK_MEASUREMENTS[1],
        frequency="5T",
    )

    captured = capsys.readouterr()
    ann_output = captured.err.split("\n")

    correct = [
        "standard_series | Mid Stream at Cowtoilet Farm",
        "import_standard | Mid Stream at Cowtoilet Farm",
        "quality_series | Mid Stream at Cowtoilet Farm",
        "import_quality | Mid Stream at Cowtoilet Farm",
        "check_series | Mid Stream at Cowtoilet Farm",
        "import_check | Mid Stream at Cowtoilet Farm",
        "__init__ | Mid Stream at Cowtoilet Farm",
    ]

    for i, out in enumerate(ann_output[0:-1]):
        assert out == correct[i], f"Failed on log number {i} with output {out}"

    assert isinstance(pr.standard_series, pd.Series)
    assert pr.raw_standard_blob is not None
    assert pr.standard_measurement_name == pr.raw_standard_blob.data_source.name
    assert float(pr.standard_series.loc["2023-01-01 00:10:00"]) == pytest.approx(1882.1)
    assert pr.standard_series.index.dtype == np.dtype("datetime64[ns]")


def test_to_xml_data_structure(
    monkeypatch,
    mock_site_list,
    mock_measurement_list,
    mock_xml_data,
    mock_qc_evaluator_dict,
    tmp_path,
    sample_data_source_xml_file,
):
    """
    Test the conversion of Processor data to XML data structure.

    Parameters
    ----------
    monkeypatch : pytest.MonkeyPatch
        Pytest fixture for monkeypatching.
    mock_site_list : List[str]
        Mocked list of site names.
    mock_measurement_list : List[str]
        Mocked list of measurement names.
    mock_xml_data : str
        Mocked XML data content.
    mock_qc_evaluator_dict : Dict[str, Any]
        Mocked QC evaluator dictionary.
    sample_data_source_xml_file : str
        Path to the sample XML data file.

    Notes
    -----
    This test function checks the conversion of Processor data to the XML data structure.
    It mocks relevant functions and classes for the test.

    Assertions
    ----------
    - The canonicalized content of the generated XML file matches the sample XML content.
    - Each data source blob in the list has a site name matching the specified site.

    """

    def get_mock_site_list(*args, **kwargs):
        _ = args, kwargs
        return mock_site_list

    def get_mock_measurement_list(*args, **kwargs):
        _ = args, kwargs
        return mock_measurement_list

    def get_mock_xml_data(*args, **kwargs):
        _ = args, kwargs
        return mock_xml_data

    def get_mock_qc_evaluator_dict(*args, **kwargs):
        _ = args, kwargs
        return mock_qc_evaluator_dict

    ann.configure(stream_format_str="%(function_name)s | %(site)s")

    # Here we patch the Hilltop Class
    monkeypatch.setattr(Hilltop, "get_site_list", get_mock_site_list)
    monkeypatch.setattr(Hilltop, "get_measurement_list", get_mock_measurement_list)
    monkeypatch.setattr(
        data_sources,
        "get_qc_evaluator_dict",
        get_mock_qc_evaluator_dict,
    )

    # However, in this case, we need to patch the INSTANCE as imported in
    # data_acquisition. Not sure if this makes sense to me, but it works.
    monkeypatch.setattr("hydrobot.data_acquisition.get_hilltop_xml", get_mock_xml_data)

    data_source_blob_list = []

    for check, meas in zip(CHECK_MEASUREMENTS, MEASUREMENTS):
        pr = processor.Processor(
            base_url="https://greenwashed.and.pleasant/",
            site=SITES[1],
            standard_hts="GreenPasturesAreNaturalAndEcoFriendlyISwear.hts",
            standard_measurement_name=meas,
            check_measurement_name=check,
            frequency="5T",
        )

        data_source_blob_list += pr.to_xml_data_structure()

    output_path = tmp_path / "output.xml"
    data_structure.write_hilltop_xml(data_source_blob_list, output_path)

    with open(output_path) as f:
        output_xml = f.read()

    with open(sample_data_source_xml_file) as f:
        sample_data_source_xml = f.read()

    input_tree = DefusedElementTree.fromstring(sample_data_source_xml)
    output_tree = DefusedElementTree.fromstring(output_xml)

    assert ElementTree.indent(input_tree) == ElementTree.indent(output_tree)

    for blob in data_source_blob_list:
        assert blob.site_name == SITES[1]


def test_import_data(
    monkeypatch,
    mock_site_list,
    mock_measurement_list,
    mock_get_data,
    mock_qc_evaluator_dict,
):
    """
    Test the import_data method of the Processor class.

    Parameters
    ----------
    monkeypatch : pytest.MonkeyPatch
        Pytest fixture for monkeypatching.
    mock_site_list : List[str]
        Mocked list of site names.
    mock_measurement_list : List[str]
        Mocked list of measurement names.
    mock_get_data : Callable
        Mocked get_data function.
    mock_qc_evaluator_dict : Dict[str, Any]
        Mocked QC evaluator dictionary.

    Notes
    -----
    This test function checks the import_data method of the Processor class.
    It mocks relevant functions and classes for the test.

    Assertions
    ----------
    - For each index in standard_series, quality_series, and check_series, it is within
        the specified date range.
    - The import_data method updates the series with new data and retains existing
        changes without overwriting.
    - The import_data method overwrites existing data when the 'overwrite' parameter
        is set to True.

    """

    def get_mock_site_list(*args, **kwargs):
        _ = args, kwargs
        return mock_site_list

    def get_mock_measurement_list(*args, **kwargs):
        _ = args, kwargs
        return mock_measurement_list

    def get_mock_get_data(*args, **kwargs):
        xml, data_func = mock_get_data
        return xml, data_func(*args, **kwargs)

    def get_mock_qc_evaluator_dict(*args, **kwargs):
        _ = args, kwargs
        return mock_qc_evaluator_dict

    ann.configure(stream_format_str="%(function_name)s | %(site)s")

    # Here we patch the Hilltop Class
    monkeypatch.setattr(Hilltop, "get_site_list", get_mock_site_list)
    monkeypatch.setattr(Hilltop, "get_measurement_list", get_mock_measurement_list)
    monkeypatch.setattr(
        data_sources,
        "get_qc_evaluator_dict",
        get_mock_qc_evaluator_dict,
    )

    # However, in this case, we need to patch the INSTANCE as imported in
    # data_acquisition. Not sure if this makes sense to me, but it works.
    monkeypatch.setattr("hydrobot.data_acquisition.get_data", get_mock_get_data)

    from_date = "2023-01-01"
    to_date = "2023/01/01 00:20"

    pr = processor.Processor(
        base_url="https://greenwashed.and.pleasant/",
        site=SITES[1],
        standard_hts="GreenPasturesAreNaturalAndEcoFriendlyISwear.hts",
        standard_measurement_name=MEASUREMENTS[0],
        frequency="5T",
        from_date=from_date,
        to_date=to_date,
    )

    for idx in pr.standard_series.index:
        assert idx >= pd.to_datetime(from_date)
        assert idx <= pd.to_datetime(to_date)

    for idx in pr.quality_series.index:
        assert idx >= pd.to_datetime(from_date)
        assert idx <= pd.to_datetime(to_date)

    for idx in pr.check_series.index:
        assert idx >= pd.to_datetime(from_date)
        assert idx <= pd.to_datetime(to_date)


def test_gap_closer(
    monkeypatch,
    mock_site_list,
    mock_measurement_list,
    mock_get_data,
    mock_qc_evaluator_dict,
):
    """
    Test the 'gap_closer' method of the Processor class.

    Parameters
    ----------
    monkeypatch : pytest.MonkeyPatch
        Pytest fixture to modify or mock modules during testing.
    mock_site_list : pytest fixture
        Mocked response for the site list.
    mock_measurement_list : pytest fixture
        Mocked response for the measurement list.
    mock_get_data : pytest fixture
        Mock response for the get_data server call method.
    mock_qc_evaluator_dict : pytest fixture
        Mocked response for the quality control evaluator dictionary.

    Notes
    -----
    - This test checks the functionality of the 'gap_closer' method in the Processor
        class.
    - It involves creating a Processor object, making a gap in the data, inserting NaNs,
        and then closing the gap.
    - Assertions are made to ensure that the gap is properly created, NaNs are inserted,
        and the gap is closed.

    Assertions
    ----------
    - The data points that are intended to be deleted actually exist before the gap
        creation.
    - After creating a small gap, check that the gap was made by confirming the absence
        of the specified data points.
    - Check that NaNs are correctly inserted into the specified positions in the data.
    - After closing the gaps, verify that the specified data points are no longer
        present in the data.

    """

    def get_mock_site_list(*args, **kwargs):
        _ = args, kwargs
        return mock_site_list

    def get_mock_measurement_list(*args, **kwargs):
        _ = args, kwargs
        return mock_measurement_list

    def get_mock_get_data(*args, **kwargs):
        xml, data_func = mock_get_data
        return xml, data_func(*args, **kwargs)

    def get_mock_qc_evaluator_dict(*args, **kwargs):
        _ = args, kwargs
        return mock_qc_evaluator_dict

    ann.configure(stream_format_str="%(function_name)s | %(site)s")

    # Here we patch the Hilltop Class
    monkeypatch.setattr(Hilltop, "get_site_list", get_mock_site_list)
    monkeypatch.setattr(Hilltop, "get_measurement_list", get_mock_measurement_list)
    monkeypatch.setattr(
        data_sources,
        "get_qc_evaluator_dict",
        get_mock_qc_evaluator_dict,
    )

    # However, in this case, we need to patch the INSTANCE as imported in
    # data_acquisition. Not sure if this makes sense to me, but it works.
    monkeypatch.setattr("hydrobot.data_acquisition.get_data", get_mock_get_data)

    pr = processor.Processor(
        base_url="https://greenwashed.and.pleasant/",
        site=SITES[1],
        standard_hts="GreenPasturesAreNaturalAndEcoFriendlyISwear.hts",
        standard_measurement_name=MEASUREMENTS[0],
        frequency="5T",
    )

    # Checking that the data points I want to delete actually exist:
    start_idx = "2023-01-01 00:20:00"
    end_idx = "2023-01-01 00:25:00"
    assert pd.to_datetime(start_idx) in pr.standard_series
    assert pd.to_datetime(end_idx) in pr.standard_series

    # Make a small gap
    pr.delete_range(start_idx, end_idx)

    # Check that gap was made
    assert (
        pd.to_datetime(start_idx) not in pr.standard_series
    ), "processor.delete_range appears to be broken."
    assert (
        pd.to_datetime(end_idx) not in pr.standard_series
    ), "processor.delete_range appears to be broken."

    # Insert nans where values are missing
    pr.insert_missing_nans()

    # Check that NaNs are inserted
    assert pd.isna(
        pr.standard_series[start_idx]
    ), "processor.insert_missing_nans appears to be broken."
    assert pd.isna(
        pr.standard_series[end_idx]
    ), "processor.insert_missing_nans appears to be broken."

    # "Close" gaps (i.e. remove nan rows)
    pr.gap_closer()

    # Check that gap was closed
    assert (
        pd.to_datetime(start_idx) not in pr.standard_series
    ), "processor.gap_closer appears to be broken."
    assert (
        pd.to_datetime(end_idx) not in pr.standard_series
    ), "processor.gap_closer appears to be broken."


def test_data_export(
    monkeypatch,
    mock_site_list,
    mock_measurement_list,
    mock_get_data,
    mock_qc_evaluator_dict,
    tmp_path,
):
    """
    Test the 'gap_closer' method of the Processor class.

    Parameters
    ----------
    monkeypatch : pytest.MonkeyPatch
        Pytest fixture to modify or mock modules during testing.
    mock_site_list : pytest fixture
        Mocked response for the site list.
    mock_measurement_list : pytest fixture
        Mocked response for the measurement list.
    mock_get_data : pytest fixture
        Mock response for the get_data server call method.
    mock_qc_evaluator_dict : pytest fixture
        Mocked response for the quality control evaluator dictionary.

    Notes
    -----
    - This test checks the functionality of the 'gap_closer' method in the Processor
        class.
    - It involves creating a Processor object, making a gap in the data, inserting NaNs,
        and then closing the gap.
    - Assertions are made to ensure that the gap is properly created, NaNs are inserted,
        and the gap is closed.

    Assertions
    ----------
    - The data points that are intended to be deleted actually exist before the gap
        creation.
    - After creating a small gap, check that the gap was made by confirming the absence
        of the specified data points.
    - Check that NaNs are correctly inserted into the specified positions in the data.
    - After closing the gaps, verify that the specified data points are no longer
        present in the data.

    """

    def get_mock_site_list(*args, **kwargs):
        _ = args, kwargs
        return mock_site_list

    def get_mock_measurement_list(*args, **kwargs):
        _ = args, kwargs
        return mock_measurement_list

    def get_mock_get_data(*args, **kwargs):
        xml, data_func = mock_get_data
        return xml, data_func(*args, **kwargs)

    def get_mock_qc_evaluator_dict(*args, **kwargs):
        _ = args, kwargs
        return mock_qc_evaluator_dict

    ann.configure(stream_format_str="%(function_name)s | %(site)s")

    # Here we patch the Hilltop Class
    monkeypatch.setattr(Hilltop, "get_site_list", get_mock_site_list)
    monkeypatch.setattr(Hilltop, "get_measurement_list", get_mock_measurement_list)
    monkeypatch.setattr(
        data_sources,
        "get_qc_evaluator_dict",
        get_mock_qc_evaluator_dict,
    )

    # However, in this case, we need to patch the INSTANCE as imported in
    # data_acquisition. Not sure if this makes sense to me, but it works.
    monkeypatch.setattr("hydrobot.data_acquisition.get_data", get_mock_get_data)

    pr = processor.Processor(
        base_url="https://greenwashed.and.pleasant/",
        site=SITES[1],
        standard_hts="GreenPasturesAreNaturalAndEcoFriendlyISwear.hts",
        standard_measurement_name=MEASUREMENTS[0],
        frequency="5T",
    )

    # Checking that the data points I want to delete actually exist:
    start_idx = "2023-01-01 00:20:00"
    end_idx = "2023-01-01 00:25:00"
    assert pd.to_datetime(start_idx) in pr.standard_series
    assert pd.to_datetime(end_idx) in pr.standard_series

    # =======================Make a small gap========================
    print("Gappy Chappy")
    pr.delete_range(start_idx, end_idx)

    gap_path_csv = tmp_path / "gap_output.csv"
    gap_path_hilltop_csv = tmp_path / "gap_output_hilltop"
    gap_path_xml = tmp_path / "gap_output.xml"

    pr.data_exporter(gap_path_csv, ftype="csv")

    read_csv_df = pd.read_csv(gap_path_csv)
    # Check that the csv was filled in with nans where there are no quality values
    assert pd.isna(read_csv_df["General Nastiness [Quality]"].iloc[1])

    # The hilltop_csv format outputs two files:
    # one for standard and qc together,
    # and one for check data alone.
    pr.data_exporter(gap_path_hilltop_csv, ftype="hilltop_csv")
    hilltop_path_std_qc = tmp_path / "gap_output_hilltop_std_qc.csv"
    hilltop_path_check = tmp_path / "gap_output_hilltop_check.csv"

    read_hilltop_std_qc_csv_df = pd.read_csv(hilltop_path_std_qc)
    read_hilltop_check_csv_df = pd.read_csv(hilltop_path_check)

    # Check that the deleted values have not been filled somehow
    assert start_idx not in list(read_hilltop_std_qc_csv_df.index)
    assert start_idx not in list(read_hilltop_check_csv_df.index)

    print("Before xml export:", pr.quality_series.index)
    pr.data_exporter(gap_path_xml, ftype="xml")
    print("After xml export:", pr.quality_series.index)
    gap_path_xml_tree = DefusedElementTree.fromstring(gap_path_xml.read_text())
    gap_path_blob = data_structure.parse_xml(gap_path_xml_tree)

    std_indices = gap_path_blob[0].data.timeseries.index
    assert pd.Timestamp(start_idx) not in list(std_indices)

    # =======================Insert Nans========================
    # This is how we internally represent gaps. They need to be converted to the Gap
    # tag for xml export.
    print("Before nans:", pr.quality_series.index)
    pr.insert_missing_nans()
    print("After nans:", pr.quality_series.index)

    pr.data_exporter(gap_path_csv, ftype="csv")

    read_csv_df = pd.read_csv(gap_path_csv)
    # Check that the csv was filled in with nans where there are no quality values
    # assert pd.isna(read_csv_df["General Nastiness [Quality]"].iloc[1])

    # The hilltop_csv format outputs two files:
    # one for standard and qc together,
    # and one for check data alone.
    pr.data_exporter(gap_path_hilltop_csv, ftype="hilltop_csv")

    read_hilltop_std_qc_csv_df = pd.read_csv(hilltop_path_std_qc)
    read_hilltop_check_csv_df = pd.read_csv(hilltop_path_check)

    # Check that the deleted values have not been filled somehow
    # assert start_idx not in list(read_hilltop_std_qc_csv_df.index)
    # assert start_idx not in list(read_hilltop_check_csv_df.index)
    print(read_hilltop_std_qc_csv_df)
    print(read_hilltop_check_csv_df)
    # assert start_idx not in list(read_hilltop_std_qc_csv_df.index)

    pr.data_exporter(gap_path_xml, ftype="xml")

    print(gap_path_xml.read_text())
    gap_path_xml_tree = DefusedElementTree.fromstring(gap_path_xml.read_text())
    gap_path_blob = data_structure.parse_xml(gap_path_xml_tree)

    std_indices = gap_path_blob[0].data.timeseries.index
    assert start_idx not in list(std_indices)
