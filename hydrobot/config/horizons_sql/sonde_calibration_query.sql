SELECT Assets.AssetID,
    AssetHistory.DateMoved AS 'DateOfAction',
    AssetHistory.Reason,
		Assets.Make,
		Assets.Model,
		Assets.LastCalibrated,
        Assets.SerialNumber,
		Assets.AssetComment,
		Assets.InServiceLocationID,
		Assets.DateMoved AS 'DateMovedToSite'
    FROM [dbo].Assets
		INNER JOIN [dbo].AssetHistory
			ON Assets.AssetID = AssetHistory.AssetID
		INNER JOIN [dbo].Sites
			ON Sites.SiteID = Assets.InServiceLocationID
      WHERE Sites.SiteName = :site
	  AND Assets.Make LIKE '%Sonde%';
