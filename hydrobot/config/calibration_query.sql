SELECT Assets.AssetID,
    AssetHistory.DateMoved AS 'DateOfAction',
    AssetHistory.Reason,
    Datasources.DataSourceName,
		Assets.Make,
		Assets.Model,
		AssetCategories.CategoryName,
		Assets.LastCalibrated,
		Assets.AssetComment,
		Assets.InServiceLocationID,
		Assets.DateMoved AS 'DateMovedToSite'
    FROM [dbo].Assets
		INNER JOIN [dbo].AssetHistory
			ON Assets.AssetID = AssetHistory.AssetID
		INNER JOIN [dbo].Sites
			ON Sites.SiteID = Assets.InServiceLocationID
		INNER JOIN [dbo].AssetCategories
			ON Assets.CategoryID = AssetCategories.CategoryID
		INNER JOIN [dbo].Datasources
			ON Assets.SensorID = Datasources.SensorID
      WHERE Sites.SiteName = :site;
