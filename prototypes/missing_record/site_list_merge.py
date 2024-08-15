"""Script for merging site list from SQL query with that from Hilltop Server."""

import platform

import pandas as pd
import sqlalchemy as db
from sqlalchemy.engine import URL

if platform.system() == "Windows":
    hostname = "SQL3.horizons.govt.nz"
elif platform.system() == "Linux":
    hostname = "PNT-DB30.horizons.govt.nz"
else:
    raise OSError("What is this, a mac? We don't do that here.")

connection_url = URL.create(
    "mssql+pyodbc",
    host=hostname,
    database="hilltop",
    query={"driver": "ODBC Driver 17 for SQL Server"},
)
engine = db.create_engine(connection_url)

sites_query = """
SELECT Sites.SiteID, SiteName
    FROM Sites
    INNER JOIN RegionSites on Sites.SiteID = RegionSites.SiteID
    INNER JOIN Regions on RegionSites.RegionID = Regions.RegionID
    WHERE
        (
            Regions.RegionName = 'CENTRAL'
            OR Regions.RegionName = 'EASTERN'
            OR Regions.RegionName = 'NORTHERN'
            OR Regions.RegionName = 'LAKES AND WQ'
        )
        AND
        (
            RecordingAuthority1 = 'MWRC'
            OR RecordingAuthority2 = 'MWRC'
        )
        AND Inactive = 0
"""

# execute the sql_query
site_list = pd.read_sql(sites_query, engine)

print(site_list.head())

measurements_query = """
SELECT MeasurementID, MeasurementName, DataSourceName
    FROM Measurements
    WHERE IsCheckDataOnly = 0
"""

measurement_list = pd.read_sql(measurements_query, engine)

measurement_list["MeasurementFullName"] = (
    measurement_list["MeasurementName"]
    + " ["
    + measurement_list["DataSourceName"]
    + "]"
)

print(measurement_list.head())
