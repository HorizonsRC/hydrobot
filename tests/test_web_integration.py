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
    Assertions are made to ensure that essential series (`standard_data`, `check_data`
    , `check_data`, `quality_data`) are not empty.
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
        "standard_hts_filename": "RawLoggerNet.hts",
        "check_hts_filename": "Archive.hts",
        "site": "Whanganui at Te Rewa",
        "from_date": "2021-06-28 00:00",
        "to_date": "2021-07-01 23:00",
        "frequency": "5min",
        "standard_measurement_name": "Stage",
        "check_measurement_name": "Water Temperature Check [Water Temperature]",
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

    with open(check_input_path, encoding="utf8") as f:
        check_input_xml = f.read()

    with open(check_output_path, encoding="utf8") as f:
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
    Assertions are made to ensure that essential series (standard_data, check_data,
    check_data, quality_data) are not empty.

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
        "standard_hts_filename": "RawLoggerNet.hts",
        "check_hts_filename": "Archive.hts",
        "site": "Whanganui at Te Rewa",
        "from_date": "2021-01-01 00:00",
        "to_date": "2021-02-02 23:00",
        "frequency": "5min",
        "standard_measurement_name": "Water level statistics: Point Sample",
        "check_measurement_name": "Water Temperature Check [Water Temperature]",
        "defaults": {
            "high_clip": 100000,
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

    assert isinstance(data.standard_data, pd.DataFrame)
    assert isinstance(data.quality_data, pd.DataFrame)
    assert isinstance(data.check_data, pd.DataFrame)

    assert not data.standard_data.empty
    assert not data.check_data.empty
    assert not data.quality_data.empty

    clip_one = "2021-01-15 12:00"
    clip_two = "2021-02-01 00:00"

    data.standard_data.loc[clip_one, "Value"] = 100001
    data.standard_data.loc[clip_two, "Value"] = -5
    data.clip()

    assert pd.isna(data.standard_data.loc[clip_one, "Value"])
    assert pd.isna(data.standard_data.loc[clip_two, "Value"])

    assert data.standard_data.loc[clip_one, "Changes"] == "CLP"
    assert data.standard_data.loc[clip_two, "Changes"] == "CLP"

    assert data.standard_data.loc[clip_one, "Remove"]
    assert data.standard_data.loc[clip_two, "Remove"]

    flat_one = "2021-01-20 12:05"
    flat_two = "2021-01-20 12:10"
    flat_three = "2021-01-20 12:15"

    flat_val = data.standard_data.loc["2021-01-20 12:00", "Value"]

    data.standard_data.loc[flat_one, "Value"] = flat_val
    data.standard_data.loc[flat_two, "Value"] = flat_val
    data.standard_data.loc[flat_three, "Value"] = flat_val
    data.remove_flatlined_values()

    assert pd.isna(data.standard_data.loc[flat_one, "Value"])
    assert pd.isna(data.standard_data.loc[flat_two, "Value"])
    assert pd.isna(data.standard_data.loc[flat_three, "Value"])

    assert data.standard_data.loc[flat_one, "Changes"] == "FLN"
    assert data.standard_data.loc[flat_two, "Changes"] == "FLN"
    assert data.standard_data.loc[flat_three, "Changes"] == "FLN"

    assert data.standard_data.loc[flat_one, "Remove"]
    assert data.standard_data.loc[flat_two, "Remove"]
    assert data.standard_data.loc[flat_three, "Remove"]

    spike = "2021-01-10 08:00"

    data.standard_data.loc[spike, "Value"] = 100

    data.remove_spikes()

    assert pd.isna(data.standard_data.loc[spike, "Value"])

    assert data.standard_data.loc[spike, "Changes"] == "SPK"

    assert data.standard_data.loc[spike, "Remove"]

    start_idx = "2021-01-05 12:00"
    end_idx = "2021-01-05 12:30"

    print(data.standard_data.loc[start_idx:end_idx])
    data.remove_range(start_idx, end_idx)
    print(data.standard_data.loc[start_idx:end_idx])

    assert pd.isna(
        data.standard_data.loc[start_idx:end_idx, "Value"]
    ).all(), "processor.remove_range appears to be broken."
    assert (
        data.standard_data.loc[start_idx:end_idx, "Changes"]
        .apply(lambda x: x == "MAN")
        .all()
    ), "processor.remove_range appears to be broken."

    # Small Gap
    start_idx = "2021-02-02 11:00"
    end_idx = "2021-02-02 11:30"

    data.delete_range(start_idx, end_idx)
    # Check that row was completely deleted
    assert (
        pd.to_datetime(start_idx) not in data.standard_data.index
    ), "processor.delete_range appears to be broken."
    assert (
        pd.to_datetime(end_idx) not in data.standard_data.index
    ), "processor.delete_range appears to be broken."

    # Insert nans where values are missing
    data.insert_missing_nans()

    # Check that NaNs are inserted
    assert pd.isna(
        data.standard_data.loc[start_idx, "Value"]
    ), "processor.insert_missing_nans appears to be broken."
    assert pd.isna(
        data.standard_data.loc[end_idx, "Value"]
    ), "processor.insert_missing_nans appears to be broken."

    # "Close" gaps (i.e. remove nan rows)
    print(data.standard_data.loc[start_idx])
    data.gap_closer()

    # Check that gap was closed
    assert (
        pd.to_datetime(start_idx) not in data.standard_data.index
    ), "processor.gap_closer appears to be broken."
    assert (
        pd.to_datetime(end_idx) not in data.standard_data.index
    ), "processor.gap_closer appears to be broken."

    # BigGap
    start_idx = "2021-01-30 00:00"
    end_idx = "2021-02-01 00:00"

    data.delete_range(start_idx, end_idx)
    # Check that row was completely deleted
    assert (
        pd.to_datetime(start_idx) not in data.standard_data.index
    ), "processor.delete_range appears to be broken."
    assert (
        pd.to_datetime(end_idx) not in data.standard_data.index
    ), "processor.delete_range appears to be broken."

    # Insert nans where values are missing
    data.insert_missing_nans()

    # Check that NaNs are inserted
    assert pd.isna(
        data.standard_data.loc[start_idx, "Value"]
    ), "processor.insert_missing_nans appears to be broken."
    assert pd.isna(
        data.standard_data.loc[end_idx, "Value"]
    ), "processor.insert_missing_nans appears to be broken."

    # "Close" gaps (i.e. remove nan rows)
    print(data.standard_data.loc[start_idx])
    data.gap_closer()

    # Check that gap was closed
    # assert (
    #     pd.to_datetime(start_idx) not in data.standard_data.index
    # ), "processor.gap_closer appears to be broken."
    # assert (
    #     pd.to_datetime(end_idx) not in data.standard_data.index
    # ), "processor.gap_closer appears to be broken."

    data.quality_encoder()

    # TODO: Write test for quality_encoder

    data.to_xml_data_structure()

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
    Assertions are made to ensure that essential series (standard_data, check_data,
    check_data, quality_data) are not empty.

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
        "standard_hts_filename": "RawLoggerNet.hts",
        "check_hts_filename": "Archive.hts",
        "site": "Whanganui at Te Rewa",
        "from_date": "1903-01-01 00:00",
        "to_date": "1903-02-02 23:00",
        "frequency": "5min",
        "standard_measurement_name": "Water level statistics: Point Sample",
        "check_measurement_name": "Water Temperature Check [Water Temperature]",
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
        assert isinstance(data.standard_data, pd.DataFrame)
        assert isinstance(data.quality_data, pd.DataFrame)
        assert isinstance(data.check_data, pd.DataFrame)

        assert data.standard_data.empty
        assert data.check_data.empty
        assert data.quality_data.empty
        assert data.raw_standard_blob is None
        assert data.raw_standard_xml is None
        assert data.raw_quality_blob is None
        assert data.raw_quality_xml is None
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
    Assertions are made to ensure that essential series (standard_data, check_data,
    check_data, quality_data) are not empty.

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
        "standard_hts_filename": "RawLoggerNet.hts",
        "check_hts_filename": "Archive.hts",
        "site": "Whanganui at Te Rewa",
        "from_date": "2003-01-01 00:00",
        "to_date": "2003-02-02 23:00",
        "frequency": "4min",
        "standard_measurement_name": "Water level statistics: Point Sample",
        "check_measurement_name": "Water Temperature Check [Water Temperature]",
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

        """
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
        """
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
            ValueError,
            match=r"Check measurement name 'Notarealmeasurement' not found ",
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
