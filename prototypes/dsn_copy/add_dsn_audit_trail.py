"""Adds an audit trail for a dsn copy consistent with copying the individual xml/hts files."""

import datetime
import getpass
import re
from pathlib import Path

import defusedxml.ElementTree as ElementTree
import pyodbc


def get_details_from_xml(source_xml):
    """Gets the details from an xml, returns details for audit."""
    details = []
    try:
        tree = ElementTree.parse(source_xml)
        root = tree.getroot()
    except ElementTree.ParseError:
        print(f"Error parsing xml {source_xml}")
        return details
    for measurement in root.findall("Measurement"):
        measurement_details = {
            "site": measurement.attrib["SiteName"],
            "data_source": measurement.find("DataSource").attrib["Name"],
            "ts_type": measurement.find("DataSource").find("TSType").text,
            "start_date": measurement.find("Data").find("E").find("T").text,
            "end_date": measurement.find("Data").findall("E")[-1].find("T").text,
        }
        details.append(measurement_details)
    return details


def write_to_access_for_single_copy(source, destination):
    """Adds an audit trail for copying an individual xml/hts file."""
    audit_destination = str(Path(destination).with_suffix(".accdb"))
    if not Path(audit_destination).exists():
        raise FileNotFoundError(f"The audit file {audit_destination} does not exist.")
    for transaction in get_details_from_xml(source):
        write_access_row(
            audit_destination,
            transaction["site"],
            transaction["data_source"],
            transaction["ts_type"],
            transaction["start_date"],
            transaction["end_date"],
            source,
        )


def write_access_row(
    access_file, site, data_source, ts_type, start_date, end_date, source
):
    """Write a single access audit entry."""
    connection_string = (
        "DRIVER={Microsoft Access Driver (*.mdb, *.accdb)};DBQ=" + access_file + ";"
    )
    cnxn = pyodbc.connect(connection_string)

    insert_query = """
        INSERT INTO Audit ("Date","UserName","Process","Site","DataSource","TsType","StartDate","EndDate","Comment")
        VALUES (?,?,?,?,?,?,?,?,?);
    """
    values = (
        datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        getpass.getuser(),
        "Copy from Site",
        site,
        data_source,
        ts_type,
        start_date,
        end_date,
        source,
    )

    cursor = cnxn.cursor()
    cursor.execute(insert_query, values)
    cursor.commit()

    cursor.close()
    cnxn.close()


def write_to_access_for_dsn(source_dsn, destination):
    """Parse dsn or other file to turn it into auditing instructions."""
    with open(source_dsn) as file:
        dsn_text = file.read()
    regex = re.compile(r'File\d*="(.*)"')
    source_file = regex.findall(dsn_text)
    for path in source_file:
        if Path(path).suffix == ".dsn":
            write_to_access_for_dsn(path, destination)
        else:
            write_to_access_for_single_copy(path, destination)


if __name__ == "__main__":
    write_to_access_for_dsn(
        r"C:\Users\SIrvine\PycharmProjects\hydro-processing-tools\prototypes\tasks_copy\output_dump\test_home\hydrobot_dsn.dsn",
        r"C:\Users\SIrvine\PycharmProjects\hydro-processing-tools\prototypes\tasks_copy\output_dump\test_home"
        r"\test_copy\test_file.hts",
    )
