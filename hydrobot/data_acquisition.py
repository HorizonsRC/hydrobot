"""Main module."""

from xml.etree import ElementTree

import pandas as pd
import yaml
from annalist.annalist import Annalist
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
    pandas.DataFrame
        A DataFrame containing the acquired time series data.
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
    print(url)

    data_object = parse_xml(hilltop_xml)

    return hilltop_xml, data_object


def get_series(
    base_url,
    hts,
    site,
    measurement,
    from_date,
    to_date,
    tstype="Standard",
) -> tuple[ElementTree.Element, pd.DataFrame]:
    """Pack data from get_data as a pd.Series.

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
    pandas.Series or pandas.DataFrame
        A pd.Series containing the acquired time series data.
    """
    xml, data_object = get_data(
        base_url,
        hts,
        site,
        measurement,
        from_date,
        to_date,
        tstype,
    )
    if data_object is not None:
        data = data_object[0].data.timeseries
        if not data.empty:
            mowsecs_offset = 946771200
            if data_object[0].data.date_format == "mowsecs":
                timestamps = data.index.map(
                    lambda x: pd.Timestamp(int(x) - mowsecs_offset, unit="s")
                )
                data.index = pd.to_datetime(timestamps)
            else:
                data.index = pd.to_datetime(data.index)
    else:
        data = pd.DataFrame({})
    return xml, data


def import_inspections(filename):
    """Import inspections as generated by R script."""
    try:
        insp_df = pd.read_csv(filename)
        if not insp_df.empty:
            insp_df["Time"] = pd.to_datetime(insp_df["Date"] + " " + insp_df["Time"])
            insp_df = insp_df.set_index("Time")
            insp_df = insp_df.drop(columns=["Date"])
            insp_df["Comment"] = insp_df.apply(
                lambda x: f"{x['InspectionStaff']}: {x['Notes']}", axis=1
            )
        else:
            insp_df = pd.DataFrame({"Time": [], "Temp Check": [], "Comment": []})
    except FileNotFoundError:
        insp_df = pd.DataFrame({"Time": [], "Temp Check": [], "Comment": []})

    insp_df["Value"] = insp_df["Temp Check"]
    insp_df["Raw"] = insp_df["Temp Check"]
    insp_df = insp_df[~insp_df["Value"].isna()]
    insp_df["Source"] = "INS"
    insp_df["QC"] = True
    return insp_df


def import_prov_wq(filename):
    """Import prov_wq checks as obtained by R script."""
    try:
        prov_df = pd.read_csv(filename)
        if not prov_df.empty:
            prov_df["Time"] = pd.to_datetime(prov_df["Date"] + " " + prov_df["Time"])
            prov_df = prov_df.set_index("Time")
            prov_df = prov_df.drop(columns=["Date"])
            prov_df["Comment"] = prov_df.apply(
                lambda x: f"{x['InspectionStaff']}: {x['Notes']}", axis=1
            )
        else:
            prov_df = pd.DataFrame({"Time": [], "Temp Check": [], "Comment": []})
    except FileNotFoundError:
        prov_df = pd.DataFrame({"Time": [], "Temp Check": [], "Comment": []})
    prov_df["Value"] = prov_df["Temp Check"]
    prov_df["Raw"] = prov_df["Temp Check"]
    prov_df = prov_df[~prov_df["Value"].isna()]
    prov_df["Source"] = "SOE"
    prov_df["QC"] = False
    return prov_df


def import_ncr(filename):
    """Import non conformance data as obtained by R script."""
    try:
        ncr_df = pd.read_csv(filename)
        if not ncr_df.empty:
            ncr_df = ncr_df.rename(columns={"Entrydate": "Time"})
            ncr_df["Time"] = pd.to_datetime(ncr_df["Time"])
            ncr_df["Comment"] = ncr_df.apply(
                lambda x: f"{x['Reportby']}: {x['NC_Summary']}; {x['CorrectiveAction']}",
                axis=1,
            )
        else:
            ncr_df = pd.DataFrame({"Time": [], "Temp Check": [], "Comment": []})
    except FileNotFoundError:
        ncr_df = pd.DataFrame({"Time": [], "Temp Check": [], "Comment": []})
    return ncr_df


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
