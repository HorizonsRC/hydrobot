"""Script for merging site list from SQL query with that from Hilltop Server."""

import pandas as pd
import pyodbc

sql_query = """
SELECT Sites.SiteID
    ,SiteName
    ,Region
    ,SubRegion
    ,RegionSites.RegionID
    ,RegionSites.RegionSiteID
    ,Regions.RegionName
    ,Regions.RegionID
    ,RecordingAuthority1
    ,RecordingAuthority2
    ,Inactive
FROM Sites
INNER JOIN RegionSites on Sites.SiteID = RegionSites.SiteID
INNER JOIN Regions on RegionSites.RegionID = Regions.RegionID
WHERE
    (

)       Regions.RegionName = 'CENTRAL'
        OR Regions.RegionName = 'EASTERN'
        OR Regions.RegionName = 'NORTHERN'
        OR Regions.RegionName = 'LAKES AND WQ'
    )
    AND
    (

)       RecordingAuthority1 = 'MWRC'
        OR RecordingAuthority2 = 'MWRC'
    )
    AND Inactive = 0
"""

con = pyodbc.connect("DRIVER={ODBC Driver 17 for SQL Server};")

# execute the query
site_list = pd.read_sql(sql_query, con)

print(site_list)
