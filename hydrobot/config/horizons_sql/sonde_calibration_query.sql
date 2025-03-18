SELECT Assets.AssetID,
    AssetHistory.DateMoved AS 'DateOfAction',
    AssetHistory.Reason,
		Assets.Make,
		Assets.Model,
		Assets.LastCalibrated,
		Assets.AssetComment,
		Assets.InServiceLocationID,
		Assets.DateMoved AS 'DateMovedToSite'
    FROM [dbo].Assets
		INNER JOIN [dbo].AssetHistory
			ON Assets.AssetID = AssetHistory.AssetID
		INNER JOIN [dbo].Sites
			ON Sites.SiteID = Assets.InServiceLocationID
      WHERE Sites.SiteName = 'Manawatu at Teachers College'
	  AND Assets.Make LIKE '%Sonde%';
