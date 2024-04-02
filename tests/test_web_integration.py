"""Test actual integration tests."""
from xml.etree import ElementTree

import pandas as pd
import pytest
from annalist.annalist import Annalist
from defusedxml import ElementTree as DefusedElementTree
from hilltoppy.utils import build_url, get_hilltop_xml

from hydrobot.data_structure import parse_xml, write_hilltop_xml
from hydrobot.processor import Processor


@pytest.mark.slow()
@pytest.mark.remote()
def test_data_structure_integration(tmp_path):
    """
    Test connection to the actual server.

    Parameters
    ----------
    tmp_path : pathlib.Path
        The temporary path for storing log files and exported data.

    Notes
    -----
    This test checks the connection to the specified server and various functionalities
    of the Processor class.
    The test configuration includes parameters such as base_url, file names,
    site information, date range, and default settings.
    Annalist is configured to log information during the test.
    Processor is instantiated with the provided processing parameters.
    Assertions are made to ensure that essential series (`standard_series`, `check_data`
    , `check_series`, `quality_series`) are not empty.
    Data clipping, removal of flatlined values and spikes, range deletion, insertion of
    missing NaNs, gap closure, quality encoding, XML data structure creation,
    data export, and diagnosis are tested.

    Assertions
    ----------
    Various assertions are included throughout the test to verify the expected behavior
    of Processor methods and properties.
    These assertions cover the state of data series before and after certain operations,
    ensuring data integrity and functionality.
    """
    processing_parameters = {
        "base_url": "http://hilltopdev.horizons.govt.nz/",
        "standard_hts_filename": "RawLogger.hts",
        "check_hts_filename": "boo.hts",
        "site": "Whanganui at Te Rewa",
        "from_date": "2021-06-28 00:00",
        "to_date": "2021-07-01 23:00",
        "frequency": "5min",
        "standard_measurement_name": "Stage",
        "check_measurement_name": "External S.G. [Water Level NRT]",
        "defaults": {
            "high_clip": 20000,
            "low_clip": 0,
            "delta": 1000,
            "span": 10,
            "gap_limit": 12,
            "max_qc": 600,
        },
    }

    # standard data

    standard_url = build_url(
        processing_parameters["base_url"],
        processing_parameters["standard_hts_filename"],
        "GetData",
        site=processing_parameters["site"],
        measurement=processing_parameters["standard_measurement_name"],
        from_date=processing_parameters["from_date"],
        to_date=processing_parameters["to_date"],
        tstype="Standard",
    )

    standard_hilltop_xml = get_hilltop_xml(standard_url)

    standard_root = ElementTree.ElementTree(standard_hilltop_xml)

    standard_input_path = tmp_path / "standard_input.xml"

    standard_root.write(standard_input_path)

    ElementTree.indent(standard_root, space="    ")

    standard_output_path = tmp_path / "standard_output.xml"

    standard_root.write(standard_output_path)

    standard_blobs = parse_xml(standard_root)

    write_hilltop_xml(standard_blobs, standard_output_path)

    with open(standard_input_path) as f:
        standard_input_xml = f.read()

    with open(standard_output_path) as f:
        standard_output_xml = f.read()

    standard_input_tree = DefusedElementTree.fromstring(standard_input_xml)
    standard_output_tree = DefusedElementTree.fromstring(standard_output_xml)

    assert ElementTree.indent(standard_input_tree) == ElementTree.indent(
        standard_output_tree
    )
    # Quality data

    quality_url = build_url(
        processing_parameters["base_url"],
        processing_parameters["standard_hts_filename"],
        "GetData",
        site=processing_parameters["site"],
        measurement=processing_parameters["standard_measurement_name"],
        tstype="Quality",
    )

    quality_hilltop_xml = get_hilltop_xml(quality_url)

    quality_root = ElementTree.ElementTree(quality_hilltop_xml)

    quality_input_path = tmp_path / "quality_input.xml"

    quality_root.write(quality_input_path)

    ElementTree.indent(quality_root, space="    ")

    quality_blobs = parse_xml(quality_root)

    quality_output_path = tmp_path / "quality_output.xml"

    write_hilltop_xml(quality_blobs, quality_output_path)

    with open(quality_input_path) as f:
        quality_input_xml = f.read()

    with open(quality_output_path) as f:
        quality_output_xml = f.read()

    quality_input_tree = DefusedElementTree.fromstring(quality_input_xml)
    quality_output_tree = DefusedElementTree.fromstring(quality_output_xml)

    assert ElementTree.indent(quality_input_tree) == ElementTree.indent(
        quality_output_tree
    )

    # Check data

    check_url = build_url(
        processing_parameters["base_url"],
        processing_parameters["check_hts_filename"],
        "GetData",
        site=processing_parameters["site"],
        measurement=processing_parameters["check_measurement_name"],
        tstype="Check",
    )

    check_hilltop_xml = get_hilltop_xml(check_url)

    check_root = ElementTree.ElementTree(check_hilltop_xml)

    check_input_path = tmp_path / "check_input.xml"

    check_root.write(check_input_path)

    ElementTree.indent(check_root, space="    ")

    check_blobs = parse_xml(check_root)

    check_output_path = tmp_path / "check_output.xml"

    write_hilltop_xml(check_blobs, check_output_path)

    with open(check_input_path) as f:
        check_input_xml = f.read()

    with open(check_output_path) as f:
        check_output_xml = f.read()

    check_input_tree = DefusedElementTree.fromstring(check_input_xml)
    check_output_tree = DefusedElementTree.fromstring(check_output_xml)

    assert ElementTree.indent(check_input_tree) == ElementTree.indent(check_output_tree)


@pytest.mark.slow()
@pytest.mark.remote()
def test_processor_integration(tmp_path):
    """
    Test connection to the actual server.

    Parameters
    ----------
    tmp_path : pathlib.Path
        The temporary path for storing log files and exported data.

    Notes
    -----
    This test checks the connection to the specified server and various functionalities
    of the Processor class. The test configuration includes parameters such as
    base_url, file names, site information, date range, and default settings.

    Annalist is configured to log information during the test.
    Processor is instantiated with the provided processing parameters.
    Assertions are made to ensure that essential series (standard_series, check_data,
    check_series, quality_series) are not empty.

    Data clipping, removal of flatlined values and spikes, range deletion, insertion of
    missing NaNs, gap closure, quality encoding, XML data structure creation, data
    export, and diagnosis are tested.

    Assertions
    ----------
    Various assertions are included throughout the test to verify the expected behavior
    of Processor methods and properties.

    These assertions cover the state of data series before and after certain
    operations, ensuring data integrity and functionality.
    """
    processing_parameters = {
        "base_url": "http://hilltopdev.horizons.govt.nz/",
        "standard_hts_filename": "RawLogger.hts",
        "check_hts_filename": "boo.hts",
        "site": "Whanganui at Te Rewa",
        "from_date": "2021-01-01 00:00",
        "to_date": "2021-02-02 23:00",
        "frequency": "5min",
        "standard_measurement_name": "Water level statistics: Point Sample",
        "check_measurement_name": "External S.G. [Water Level NRT]",
        "defaults": {
            "high_clip": 5000,
            "low_clip": 0,
            "delta": 1000,
            "span": 10,
            "gap_limit": 12,
            "max_qc": 600,
        },
    }

    ann = Annalist()
    format_str = format_str = (
        "%(asctime)s, %(analyst_name)s, %(function_name)s, %(site)s, "
        "%(measurement)s, %(from_date)s, %(to_date)s, %(message)s"
    )
    ann.configure(
        logfile=tmp_path / "bot_annals.csv",
        analyst_name="Annie the analyst!",
        stream_format_str=format_str,
    )

    data = Processor(
        processing_parameters["base_url"],
        processing_parameters["site"],
        processing_parameters["standard_hts_filename"],
        processing_parameters["standard_measurement_name"],
        processing_parameters["frequency"],
        processing_parameters["from_date"],
        processing_parameters["to_date"],
        processing_parameters["check_hts_filename"],
        processing_parameters["check_measurement_name"],
        processing_parameters["defaults"],
    )

    assert not data.standard_series.empty
    assert not data.check_series.empty
    assert not data.quality_series.empty

    standard_before_clip = data.standard_series
    check_before_clip = data.check_series

    data.clip()

    standard_after_clip = data.standard_series
    check_after_clip = data.check_series

    assert not standard_before_clip.equals(standard_after_clip)
    assert check_before_clip.equals(check_after_clip)

    assert (
        data.standard_series[
            standard_before_clip > processing_parameters["defaults"]["high_clip"]
        ]
        .isna()
        .all()
    )
    assert (
        data.check_series[
            check_before_clip > processing_parameters["defaults"]["high_clip"]
        ]
        .isna()
        .all()
    )

    data.remove_flatlined_values()
    # TODO: Write test for remove_flatlined_values

    data.remove_spikes()
    # TODO: Write test for remove_spikes

    # Checking that the data points I want to delete actually exist:
    start_idx = "2021-01-01 11:00"
    end_idx = "2021-01-01 11:30"
    assert pd.to_datetime(start_idx) in data.standard_series
    assert pd.to_datetime(end_idx) in data.standard_series

    # Make a small gap
    data.delete_range(start_idx, end_idx)

    # Check that gap was made
    assert (
        pd.to_datetime(start_idx) not in data.standard_series
    ), "processor.delete_range appears to be broken."
    assert (
        pd.to_datetime(end_idx) not in data.standard_series
    ), "processor.delete_range appears to be broken."

    # Insert nans where values are missing
    data.insert_missing_nans()

    # Check that NaNs are inserted
    assert pd.isna(
        data.standard_series[start_idx]
    ), "processor.insert_missing_nans appears to be broken."
    assert pd.isna(
        data.standard_series[end_idx]
    ), "processor.insert_missing_nans appears to be broken."

    # "Close" gaps (i.e. remove nan rows)
    data.gap_closer()

    # Check that gap was closed
    assert (
        pd.to_datetime(start_idx) not in data.standard_series
    ), "processor.gap_closer appears to be broken."
    assert (
        pd.to_datetime(end_idx) not in data.standard_series
    ), "processor.gap_closer appears to be broken."

    data.quality_encoder()

    # TODO: Write test for quality_encoder

    data.to_xml_data_structure()

    # TODO: Write test for to_xml_data_structure

    data.data_exporter(tmp_path / "xml_data.xml")
    data.data_exporter(tmp_path / "csv_data.csv", ftype="csv")
    data.data_exporter(tmp_path / "hilltop_csv_data.csv", ftype="hilltop_csv")

    # TODO: Write tests for data_exporter

    data.diagnosis()


@pytest.mark.slow()
@pytest.mark.remote()
def test_empty_response(tmp_path):
    """
    Test the handling of an empty server response.

    Parameters
    ----------
    tmp_path : pathlib.Path
        The temporary path for storing log files and exported data.

    Notes
    -----
    This test checks the connection to the specified server and various functionalities
    of the Processor class.

    The test configuration includes parameters such as base_url, file names, site
    information, date range, and default settings.

    Annalist is configured to log information during the test.
    Processor is instantiated with the provided processing parameters.
    Assertions are made to ensure that essential series (standard_series, check_data,
    check_series, quality_series) are not empty.

    Data clipping, removal of flatlined values and spikes, range deletion, insertion of
    missing NaNs, gap closure, quality encoding, XML data structure creation, data
    export, and diagnosis are tested.

    Assertions
    ----------
    Various assertions are included throughout the test to verify the expected behavior
    of Processor methods and properties.
    These assertions cover the state of data series before and after certain
    operations, ensuring data integrity and functionality.
    """
    processing_parameters = {
        "base_url": "http://hilltopdev.horizons.govt.nz/",
        "standard_hts_filename": "RawLogger.hts",
        "check_hts_filename": "boo.hts",
        "site": "Whanganui at Te Rewa",
        "from_date": "2003-01-01 00:00",
        "to_date": "2003-02-02 23:00",
        "frequency": "5min",
        "standard_measurement_name": "Water level statistics: Point Sample",
        "check_measurement_name": "External S.G. [Water Level NRT]",
        "defaults": {
            "high_clip": 5000,
            "low_clip": 0,
            "delta": 1000,
            "span": 10,
            "gap_limit": 12,
            "max_qc": 600,
        },
    }

    with pytest.warns(UserWarning):
        ann = Annalist()
        format_str = format_str = (
            "%(asctime)s, %(analyst_name)s, %(function_name)s, %(site)s, "
            "%(measurement)s, %(from_date)s, %(to_date)s, %(message)s"
        )
        ann.configure(
            logfile=tmp_path / "bot_annals.csv",
            analyst_name="Annie the analyst!",
            stream_format_str=format_str,
        )

        data = Processor(
            processing_parameters["base_url"],
            processing_parameters["site"],
            processing_parameters["standard_hts_filename"],
            processing_parameters["standard_measurement_name"],
            processing_parameters["frequency"],
            processing_parameters["from_date"],
            processing_parameters["to_date"],
            processing_parameters["check_hts_filename"],
            processing_parameters["check_measurement_name"],
            processing_parameters["defaults"],
        )

        assert data.standard_series.empty
        assert data.check_series.empty
        assert data.quality_series.empty
        assert data.raw_standard_series.empty
        assert data.raw_standard_blob is None
        assert data.raw_standard_xml is None
        assert data.raw_quality_series.empty
        assert data.raw_quality_blob is None
        assert data.raw_quality_xml is None
        assert data.raw_check_data.empty
        assert data.raw_check_blob is None
        assert data.raw_check_xml is None


@pytest.mark.slow()
@pytest.mark.remote()
def test_failed_requests(tmp_path):
    """
    Test the handling of an empty server response.

    Parameters
    ----------
    tmp_path : pathlib.Path
        The temporary path for storing log files and exported data.

    Notes
    -----
    This test checks the connection to the specified server and various functionalities
    of the Processor class.

    The test configuration includes parameters such as base_url, file names, site
    information, date range, and default settings.

    Annalist is configured to log information during the test.
    Processor is instantiated with the provided processing parameters.
    Assertions are made to ensure that essential series (standard_series, check_data,
    check_series, quality_series) are not empty.

    Data clipping, removal of flatlined values and spikes, range deletion, insertion of
    missing NaNs, gap closure, quality encoding, XML data structure creation, data
    export, and diagnosis are tested.

    Assertions
    ----------
    Various assertions are included throughout the test to verify the expected behavior
    of Processor methods and properties.
    These assertions cover the state of data series before and after certain
    operations, ensuring data integrity and functionality.
    """
    processing_parameters = {
        "base_url": "http://hilltopdev.horizons.govt.nz/",
        "standard_hts_filename": "RawLogger.hts",
        "check_hts_filename": "boo.hts",
        "site": "Whanganui at Te Rewa",
        "from_date": "2003-01-01 00:00",
        "to_date": "2003-02-02 23:00",
        "frequency": "4min",
        "standard_measurement_name": "Water level statistics: Point Sample",
        "check_measurement_name": "External S.G. [Water Level NRT]",
        "defaults": {
            "high_clip": 5000,
            "low_clip": 0,
            "delta": 1000,
            "span": 10,
            "gap_limit": 12,
            "max_qc": 600,
        },
    }

    with pytest.warns(UserWarning):
        ann = Annalist()
        format_str = format_str = (
            "%(asctime)s, %(analyst_name)s, %(function_name)s, %(site)s, "
            "%(measurement)s, %(from_date)s, %(to_date)s, %(message)s"
        )
        ann.configure(
            logfile=tmp_path / "bot_annals.csv",
            analyst_name="Annie the analyst!",
            stream_format_str=format_str,
        )

        # with pytest.raises(
        #     ValueError
        # ) as excinfo:
        #     _ = Processor(
        #         processing_parameters["base_url"],
        #         processing_parameters["site"],
        #         processing_parameters["standard_hts_filename"],
        #         processing_parameters["standard_measurement_name"],
        #         processing_parameters["frequency"],
        #         processing_parameters["from_date"],
        #         processing_parameters["to_date"],
        #         processing_parameters["check_hts_filename"],
        #         processing_parameters["check_measurement_name"],
        #         processing_parameters["defaults"],
        #     )
        # print(excinfo.value)

        with pytest.raises(
            ValueError, match=r"No sites found for the base_url and hts combo."
        ) as excinfo:
            _ = Processor(
                processing_parameters["base_url"],
                processing_parameters["site"],
                "Notarealhstfile",
                # processing_parameters["standard_hts_filename"],
                processing_parameters["standard_measurement_name"],
                processing_parameters["frequency"],
                processing_parameters["from_date"],
                processing_parameters["to_date"],
                processing_parameters["check_hts_filename"],
                processing_parameters["check_measurement_name"],
                processing_parameters["defaults"],
            )
        assert "No sites found for the base_url and hts combo." in str(excinfo.value)

        with pytest.raises(
            ValueError, match=r"Site 'Notarealsite' not found .*"
        ) as excinfo:
            _ = Processor(
                processing_parameters["base_url"],
                "Notarealsite",
                processing_parameters["standard_hts_filename"],
                processing_parameters["standard_measurement_name"],
                processing_parameters["frequency"],
                processing_parameters["from_date"],
                processing_parameters["to_date"],
                processing_parameters["check_hts_filename"],
                processing_parameters["check_measurement_name"],
                processing_parameters["defaults"],
            )
        assert "Site 'Notarealsite' not found for both base_url and hts combos." in str(
            excinfo.value
        )

        with pytest.raises(ValueError, match=r"Standard measurement name.*") as excinfo:
            _ = Processor(
                processing_parameters["base_url"],
                processing_parameters["site"],
                processing_parameters["standard_hts_filename"],
                # processing_parameters["standard_measurement_name"],
                "Notarealmeasurement",
                processing_parameters["frequency"],
                processing_parameters["from_date"],
                processing_parameters["to_date"],
                processing_parameters["check_hts_filename"],
                processing_parameters["check_measurement_name"],
                processing_parameters["defaults"],
            )
        assert (
            "Standard measurement name 'Notarealmeasurement' not found at site"
            in str(excinfo.value)
        )

        with pytest.raises(
            ValueError,
            match=r"Unrecognised start time",
        ) as excinfo:
            _ = Processor(
                processing_parameters["base_url"],
                processing_parameters["site"],
                processing_parameters["standard_hts_filename"],
                processing_parameters["standard_measurement_name"],
                processing_parameters["frequency"],
                # processing_parameters["from_date"],
                "Notarealdate",
                processing_parameters["to_date"],
                processing_parameters["check_hts_filename"],
                processing_parameters["check_measurement_name"],
                processing_parameters["defaults"],
            )
        assert "Unrecognised start time" in str(excinfo.value)

        # with pytest.raises(
        #     ValueError  #, match=r"Unrecognised start time",
        # ) as excinfo:
        _ = Processor(
            processing_parameters["base_url"],
            processing_parameters["site"],
            processing_parameters["standard_hts_filename"],
            processing_parameters["standard_measurement_name"],
            # processing_parameters["frequency"],
            "Notarealfrequency",
            processing_parameters["from_date"],
            processing_parameters["to_date"],
            processing_parameters["check_hts_filename"],
            processing_parameters["check_measurement_name"],
            processing_parameters["defaults"],
        )
        print(excinfo)
        # assert (
        #     "Unrecognised start time"
        #     in str(excinfo.value)
        # )

        with pytest.raises(
            ValueError, match=r"No sites found for the base_url and hts combo."
        ) as excinfo:
            _ = Processor(
                processing_parameters["base_url"],
                processing_parameters["site"],
                processing_parameters["standard_hts_filename"],
                processing_parameters["standard_measurement_name"],
                processing_parameters["frequency"],
                processing_parameters["from_date"],
                processing_parameters["to_date"],
                # processing_parameters["check_hts_filename"],
                "Notarealhtsfilename",
                processing_parameters["check_measurement_name"],
                processing_parameters["defaults"],
            )
        assert "No sites found for the base_url and hts combo." in str(excinfo.value)

        with pytest.raises(
            ValueError, match=r"Check measurement name 'Notarealmeasurement' not found "
        ) as excinfo:
            _ = Processor(
                processing_parameters["base_url"],
                processing_parameters["site"],
                processing_parameters["standard_hts_filename"],
                processing_parameters["standard_measurement_name"],
                processing_parameters["frequency"],
                processing_parameters["from_date"],
                processing_parameters["to_date"],
                processing_parameters["check_hts_filename"],
                # processing_parameters["check_measurement_name"],
                "Notarealmeasurement",
                processing_parameters["defaults"],
            )
        print(excinfo)
        assert "Check measurement name 'Notarealmeasurement' not found at site " in str(
            excinfo.value
        )
