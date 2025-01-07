SELECT Hydro_Inspection.id,
    Hydro_Inspection.arrival_time,
    Hydro_Inspection.sitename,
    Hydro_Inspection.weather,
    Hydro_Inspection.notes,
    Hydro_Inspection.departure_time,
    Hydro_Inspection.creator,
    DO_Inspection.inspection_id as 'do_inspection_id',
    DO_Inspection.do_notes,
    WaterLevel_Inspection.inspection_id as 'wl_inspection_id',
    WaterLevel_Inspection.wl_notes,
    WaterTemp_Inspection.inspection_id as 'wt_inspection_id',
    WaterTemp_Inspection.inspection_time,
    WaterTemp_Inspection.wt_device,
    WaterTemp_Inspection.handheld_temp,
    WaterTemp_Inspection.logger_temp
FROM [dbo].Hydro_Inspection
    FULL JOIN [dbo].DO_Inspection ON DO_Inspection.inspection_id = Hydro_Inspection.id
    FULL JOIN [dbo].WaterLevel_Inspection ON WaterLevel_Inspection.inspection_id = Hydro_Inspection.id
    FULL JOIN [dbo].WaterTemp_Inspection ON WaterTemp_Inspection.inspection_id = Hydro_Inspection.id
WHERE Hydro_Inspection.sitename = :site
    AND Hydro_Inspection.arrival_time >= :start_time
    AND Hydro_Inspection.arrival_time <= :end_time
ORDER BY Hydro_Inspection.arrival_time ASC
