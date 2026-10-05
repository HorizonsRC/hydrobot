SELECT TOP (1000)
    Hydro_Inspection.id,
    Hydro_Inspection.arrival_time,
    Hydro_Inspection.sitename,
    Hydro_Inspection.weather,
    Hydro_Inspection.notes,
    Hydro_Inspection.departure_time,
    Hydro_Inspection.creator,
    [Conductivity_Inspection].inspection_time,
    [Conductivity_Inspection].handheld_cond,
	[Conductivity_Inspection].logger_cond,
    [Conductivity_Inspection].cond_calibration,
    [Conductivity_Inspection].cond_notes
FROM [dbo].Hydro_Inspection
    FULL JOIN [dbo].[Conductivity_Inspection] ON [Conductivity_Inspection].inspection_id = Hydro_Inspection.id
WHERE Hydro_Inspection.sitename = :site
    AND Hydro_Inspection.arrival_time >= :start_time
    AND Hydro_Inspection.arrival_time <= :end_time
ORDER BY Hydro_Inspection.arrival_time ASC
