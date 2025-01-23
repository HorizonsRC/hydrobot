SELECT TOP (1000)
    Hydro_Inspection.id,
    Hydro_Inspection.arrival_time,
    Hydro_Inspection.sitename,
    Hydro_Inspection.weather,
    Hydro_Inspection.notes,
    Hydro_Inspection.departure_time,
    Hydro_Inspection.creator,
    DO_Inspection.inspection_time,
    DO_Inspection.handheld_percent,
	DO_Inspection.logger_percent,
    DO_Inspection.handheld_concentration,
	DO_Inspection.handheld_baro,
    DO_Inspection.do_notes,
    WaterLevel_Inspection.wl_notes
FROM [dbo].Hydro_Inspection
    FULL JOIN [dbo].DO_Inspection ON DO_Inspection.inspection_id = Hydro_Inspection.id
    FULL JOIN [dbo].WaterLevel_Inspection ON WaterLevel_Inspection.inspection_id = Hydro_Inspection.id
WHERE Hydro_Inspection.sitename = :site
    AND Hydro_Inspection.arrival_time >= :start_time
    AND Hydro_Inspection.arrival_time <= :end_time
ORDER BY Hydro_Inspection.arrival_time ASC
