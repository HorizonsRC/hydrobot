"""Main module.

Rewritten to use whurl as the Hilltop client provider instead of hilltoppy.
This file exposes a small Hilltop wrapper that provides the minimal API used elsewhere
in hydrobot (available_sites and get_hilltop_xml, etc), and reimplements get_data,
get_time_range/get_server_dataframe to fetch raw XML via the whurl request objects so
the rest of hydrobot can continue to parse xml with hydrobot.data_structure.parse_xml.
"""

import pandas as pd
import yaml
from whurl.client import HilltopClient
from whurl.requests import GetDataRequest, TimeRangeRequest

from hydrobot.data_structure import parse_xml


class Hilltop:
    """
    Compatibility wrapper preserving the simple interface hydrobot expects.

    TEMPORARY WRAPPER FOR TRANSITION FROM hilltop-py TO whurl.

    Contains the following compatible members:
        - Hilltop(base_url, hts)
        - .available_sites property
        - get_hilltop_xml(...) method for raw XML retrieval (used by legacy code paths)
    Internally uses whurl.client.HilltopClient.
    """

    def __init__(self, base_url: str, hts: str):
        self.base_url = base_url
        # In whurl, the HTS service is called hts_endpoint; we store it here
        self.hts = hts
        # Create a synchronous client instance we can reuse for the lifetime of this
        # wrapper
        self._client = HilltopClient(base_url, hts)

    @property
    def available_sites(self) -> list[str]:
        """
        Return a list of site names available in the HTS.

        Whurl returns a SiteListResponse with .site_list entries that have .name
        attributes
        """
        resp = self.client.get_site_list()
        # Whurl SiteListResponse has .site_list entries with .name attributes
        try:
            return [site.name for site in resp.site_list]
        except Exception:
            # Fall back to DataFrame conversion if that shape is present
            try:
                return list(resp.to_dataframe().iloc[:, 0].astype(str))
            except Exception:
                return []

    def get_hilltop_xml(
        self,
        *,
        site: str | None = None,
        measurement: str | None = None,
        from_datetime: str | None = None,
        to_datetime: str | None = None,
        tstype: str | None = None,
    ) -> str:
        """
        Build a GetDataRequest and fetch raw XML using the whurl client's session.

        Returning raw XML keeps hydrobot.data_structure.parse_xml usage unchanged
        in the codebase for now.
        """
        req = GetDataRequest(
            base_url=self.base_url,
            hts_endpoint=self.hts,
            site=site,
            measurement=measurement,
            from_datetime=from_datetime,
            to_datetime=to_datetime,
            tstype=tstype,
        )
        # Use the client's session to perform the GET so we have the raw response text
        resp = self._client.session.get(req.gen_url())
        resp.raise_for_status()
        return resp.text


def get_data(
    base_url: str,
    hts: str,
    site: str,
    measurement: str,
    from_date: str | None,
    to_date: str | None,
    tstype: str = "Standard",
):
    """Acquire time series data from a web service and return it as a DataFrame.

    COMPATIBLE REPLACEMENT FOR THE OLD HILLTOP-PY BACKED GET_DATA.

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
    # Build a whurl GetDataRequest to get the same URL as hilltoppy code would have.
    req = GetDataRequest(
        base_url=base_url,
        hts_endpoint=hts,
        site=site,
        measurement=measurement,
        from_datetime=from_date,
        to_datetime=to_date,
        tstype=tstype,
    )
    # Use a short-lived client for this simple wrapper.
    # In future, we need to refactor the calling code to use a persistent client.

    client = HilltopClient(base_url, hts)
    response = client.session.get(req.gen_url())
    response.raise_for_status()
    hilltop_xml = response.text

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

    COMPATIBLE REPLACEMENT FOR THE OLD HILLTOP-PY BACKED GET_DATA.

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
    Element
        XML element from the server call
    [DataSourceBlob]
        A list of DataSourceBlobs corresponding to all measurements contained in the
        acquired time series data.
    """
    req = TimeRangeRequest(
        base_url=base_url,
        hts_endpoint=hts,
        site=site,
        measurement=measurement,
        tstype=tstype,
    )
    client = HilltopClient(base_url, hts)
    response = client.session.get(req.gen_url())
    response.raise_for_status()

    hilltop_xml = response.text
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

    COMPATIBLE REPLACEMENT FOR THE OLD HILLTOP-PY BACKED GET_DATA.

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
    from_date : str | pd.Timestamp
        The start date and time for data retrieval
        in the format 'YYYY-MM-DD HH:mm'.
    to_date : str | pd.Timestamp
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
    xml, blob = get_data(
        base_url, hts, site, measurement, from_date, to_date, tstype=tstype
    )

    if blob:
        try:
            first = blob[0]
            return first.data.timeseries.copy()
        except Exception:
            # Fallback: empty DataFrame
            return pd.DataFrame()
    return pd.DataFrame()


def get_depth_profiles(
    base_url: str,
    hts: str,
    site: str,
    measurement: str,
    from_date: str | None,
    to_date: str | None,
    tstype: str = "Standard",
) -> [pd.Series]:
    """
    Call hilltop server for depth profiles.

    COMPATIBLE REPLACEMENT FOR THE OLD HILLTOP-PY BACKED GET_DEPTH_PROFILES.

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
    from_date : str | pd.Timestamp
        The start date and time for data retrieval
        in the format 'YYYY-MM-DD HH:mm'.
    to_date : str | pd.Timestamp
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
    xml, blobs = get_data(
        base_url, hts, site, measurement, from_date, to_date, tstype=tstype
    )
    profiles = []
    if blobs:
        for b in blobs:
            profiles.append(b.data.timeseries.iloc[:, 0])
    return profiles


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

    return processing_parameters


def convert_inspection_expiry(processing_parameters):
    """
    Interpret inspection_expiry dict as pd.DateOffset.

    Parameters
    ----------
    processing_parameters : dict

    Returns
    -------
    dict
        processing_parameters with inspection_expiry converted to pd.DateOffset
    """
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
