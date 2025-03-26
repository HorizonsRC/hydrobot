"""Main module."""

import pandas as pd
import yaml
from annalist.annalist import Annalist
from hilltoppy import Hilltop
from hilltoppy.utils import build_url, get_hilltop_xml

from hydrobot.data_structure import parse_xml

annalizer = Annalist()


def get_data(
    base_url,
    hts,
    site,
    measurement,
    from_date,
    to_date,
    tstype="Standard",
):
    """Acquire time series data from a web service and return it as a DataFrame.

    Parameters
    ----------
    base_url : str
        The base URL of the web service.
    hts : str
        The Hilltop Time Series (HTS) identifier.
    site : str
        The site name or location.
    measurement : str
        The type of measurement to retrieve.
    from_date : str
        The start date and time for data retrieval
        in the format 'YYYY-MM-DD HH:mm'.
    to_date : str
        The end date and time for data retrieval
        in the format 'YYYY-MM-DD HH:mm'.
    tstype : str
        Type of data that is sought
        (default is Standard, can be Standard, Check, or Quality)

    Returns
    -------
    xml.etree.ElementTree
        An XML tree containing the acquired time series data.
    [DataSourceBlob]
        XML tree parsed to DataSourceBlobs
    """
    url = build_url(
        base_url,
        hts,
        "GetData",
        site=site,
        measurement=measurement,
        from_date=from_date,
        to_date=to_date,
        tstype=tstype,
    )

    hilltop_xml = get_hilltop_xml(url)

    data_object = parse_xml(hilltop_xml)

    return hilltop_xml, data_object


def get_time_range(
    base_url,
    hts,
    site,
    measurement,
    tstype="Standard",
):
    """Acquire time series data from a web service and return it as a DataFrame.

    Parameters
    ----------
    base_url : str
        The base URL of the web service.
    hts : str
        The Hilltop Time Series (HTS) identifier.
    site : str
        The site name or location.
    measurement : str
        The type of measurement to retrieve.
    tstype : str
        Type of data that is sought
        (default is Standard, can be Standard, Check, or Quality)

    Returns
    -------
    pandas.DataFrame
        A DataFrame containing the acquired time series data.
    """
    url = build_url(
        base_url,
        hts,
        "TimeRange",
        site=site,
        measurement=measurement,
        tstype=tstype,
    )

    hilltop_xml = get_hilltop_xml(url)

    data_object = parse_xml(hilltop_xml)

    return hilltop_xml, data_object


def get_server_dataframe(
    base_url,
    hts,
    site,
    measurement,
    from_date,
    to_date,
    tstype="Standard",
) -> pd.DataFrame:
    """
    Call hilltop server and transform to pd.DataFrame.

    Parameters
    ----------
    base_url : str
        The base URL of the web service.
    hts : str
        The Hilltop Time Series (HTS) identifier.
    site : str
        The site name or location.
    measurement : str
        The type of measurement to retrieve.
    from_date : str
        The start date and time for data retrieval
        in the format 'YYYY-MM-DD HH:mm'.
    to_date : str
        The end date and time for data retrieval
        in the format 'YYYY-MM-DD HH:mm'.
    tstype : str
        Type of data that is sought
        (default 'Standard', can be Standard, Check, or Quality)

    Returns
    -------
    pandas.DataFrame
        A dataframe containing the acquired time series data.

    Raises
    ------
    KeyError
        if there is no measurement for the given parameters
    """
    url = build_url(
        base_url,
        hts,
        "GetData",
        site=site,
        measurement=measurement,
        from_date=from_date,
        to_date=to_date,
        tstype=tstype,
    )

    root = get_hilltop_xml(url)
    data_list = []
    if root.find("Measurement") is None:
        raise KeyError(f"No measurement at the url: {url}")

    for child in root.find("Measurement").find("Data"):
        if child.tag == "E":
            data_dict = {}
            for element in child:
                if element.tag == "Parameter":
                    data_dict[element.attrib["Name"]] = element.attrib["Value"]

                else:
                    data_dict[element.tag] = element.text

            data_list += [data_dict]
        elif child.tag == "V":
            if child.text is not None:
                timestamp, data_val = child.text.split(" ")
                data_dict = {
                    "T": timestamp,
                    "V": data_val,
                }
                data_list += [data_dict]
        elif child.tag == "Gap":
            pass
        else:
            raise ValueError(
                "Possibly Malformed XML: Data items not tagged with 'E' or 'V'."
            )

    timeseries = pd.DataFrame(data_list).set_index("T")
    return timeseries


def get_depth_profiles(
    base_url,
    hts,
    site,
    measurement,
    from_date,
    to_date,
    tstype="Standard",
) -> [pd.Series]:
    """
    Call hilltop server for depth profiles.

    Parameters
    ----------
    base_url : str
        The base URL of the web service.
    hts : str
        The Hilltop Time Series (HTS) identifier.
    site : str
        The site name or location.
    measurement : str
        The type of measurement to retrieve.
    from_date : str
        The start date and time for data retrieval
        in the format 'YYYY-MM-DD HH:mm'.
    to_date : str
        The end date and time for data retrieval
        in the format 'YYYY-MM-DD HH:mm'.
    tstype : str
        Type of data that is sought
        (default 'Standard', can be Standard, Check, or Quality)

    Returns
    -------
    [pandas.Series]
        A list of pandas series each giving a depth profile.

    Raises
    ------
    KeyError
        if there is no measurement for the given parameters
    """
    url = build_url(
        base_url,
        hts,
        "GetData",
        site=site,
        measurement=measurement,
        from_date=from_date,
        to_date=to_date,
        tstype=tstype,
    )

    root = get_hilltop_xml(url)
    if root.find("Section") is None:
        raise KeyError(f"No depth profiles at the url: {url}")

    depth_profiles = {}
    for child in root:
        if child.tag == "Section":
            data_dict = {}
            for element in child.find("Data"):
                data_dict[float(element.find("O").text)] = float(
                    element.find("I1").text
                )

            depth_profiles[pd.Timestamp(child.find("SurveyTime").text)] = pd.Series(
                data_dict
            )

    return depth_profiles


def config_yaml_import(file_name: str):
    """
    Import config.yaml.

    Parameters
    ----------
    file_name : str
        Path to config.yaml

    Returns
    -------
    dict
        For inputting into processor processing_parameters
    """
    with open(file_name) as yaml_file:
        processing_parameters = yaml.safe_load(yaml_file)

    if "inspection_expiry" in processing_parameters:
        a = processing_parameters["inspection_expiry"]
        d = {}
        for key in a:
            d[pd.DateOffset(**a[key])] = key
        processing_parameters["inspection_expiry"] = d

    return processing_parameters


def enforce_site_in_hts(hts: Hilltop, site: str):
    """Raise exception if site not in Hilltop file."""
    if site not in hts.available_sites:
        raise ValueError(
            f"Site '{site}' not found in hilltop file."
            f"Available sites in {hts} are: "
            f"{[s for s in hts.available_sites]}"
        )
