SELECT TOP (1000) [objectid]
      ,[globalid]
      ,[dt] as "Arrival Time"
      ,COALESCE([Sites].[SiteName],NewSite) AS sitename
      ,[Tech]
      ,[OtherTech]
      ,[Topography]
      ,[Exposure] AS "Wind Exposure"
      ,[Obstruction] AS "Obstructed Horizon"
      ,[Distance] AS "Distance Between Gauges"
      ,[SplashGuard]
      ,[PROrificeHeight] AS "Orifice Height - Primary Reference Gauge"
      ,[PROrificeDiameter] AS "Orifice Diameter - Primary Reference Gauge"
      ,[IGOrificeHeight] AS "Orifice Height - Intensity Gauge"
      ,[IGOrificeDiameter] AS "Orifice Diameter - Intensity Gauge"
      ,[DataAffect] AS "Potential effects on Data"
      ,[Notes]
      ,[CreationDate]
      ,[Creator]
      ,[EditDate]
      ,[Editor]
  FROM [survey123].[dbo].[Rainfall Site Survey 20220510_Rainfall_Site_Survey_20220510]
	LEFT JOIN [dbo].[Sites] ON [Sites].SiteID = [Rainfall Site Survey 20220510_Rainfall_Site_Survey_20220510].[SiteName]
WHERE COALESCE([Sites].[SiteName],NewSite) = :site
ORDER BY dt ASC
