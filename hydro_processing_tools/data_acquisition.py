"""Main module."""

from hilltoppy import web_service as ws

def get_data(
    base_url,
    hts,
    site,
    measurement,
    from_date,
    to_date,
    dtl_method,
):
    """
    Acquire time series data from a web service and return it as a DataFrame.

    Parameters:
    -----------
    base_url : str
        The base URL of the web service.

    hts : str
        The Hilltop Time Series (HTS) identifier.

    site : str
        The site name or location.

    measurement : str
        The type of measurement to retrieve.

    from_date : str
        The start date and time for data retrieval in the format 'YYYY-MM-DD HH:mm'.

    to_date : str
        The end date and time for data retrieval in the format 'YYYY-MM-DD HH:mm'.

    dtl_method : str
        The data retrieval method, e.g., 'trend'.

    Returns:
    --------
    pandas.DataFrame
        A DataFrame containing the acquired time series data.
    """
    tsdata = ws.get_data(
        base_url, hts, site, measurement, from_date=from_date, to_date=to_date
    )

    return tsdata
