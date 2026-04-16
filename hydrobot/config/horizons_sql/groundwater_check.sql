SELECT TOP (1000) WL.[inspection_time]
	  ,HI.sitename
      ,WL.[creator]
      ,HI.[notes]
      ,WL.[groundwater_inspection]
      ,WL.[clarity]
      ,WL.[esg_mm]
      ,WL.[esg_error]
      ,WL.[laser_raw_mm]
      ,WL.[laser_error]
      ,WL.[laser_benchmark]
      ,WL.[laser_corrected_mm]
      ,WL.[epb_mm]
      ,WL.[logger_mm]
      ,WL.[logger_backup_mm]
      ,WL.[wl_notes]
	  ,HI.[arrival_time]
	  ,HI.[departure_time]
      ,HI.[weather]
      ,HI.[hazards_reviewed]
      ,HI.[photos_taken]
      ,HI.[climate_inspection]
      ,HI.[do_inspection]
      ,HI.[ph_inspection]
      ,HI.[conductivity_inspection]
      ,HI.[rainfall_inspection]
      ,HI.[soe_inspection]
      ,HI.[turbidity_inspection]
      ,HI.[wlevel_inspection]
      ,HI.[wtemp_inspection]
	  ,WL.[lake_inspection]
	  ,WL.[wl_id]
      ,WL.[inspection_id]
  FROM [survey123].[dbo].[WaterLevel_Inspection] AS WL
    FULL JOIN [dbo].Hydro_Inspection AS HI ON WL.inspection_id = HI.id
WHERE HI.sitename = :site
    AND HI.arrival_time >= :start_time
    AND HI.arrival_time <= :end_time
ORDER BY HI.arrival_time ASC
