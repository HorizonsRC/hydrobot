SELECT TOP (1000)
    Hydro_Inspection.id,
    Hydro_Inspection.arrival_time,
    Hydro_Inspection.sitename,
    Hydro_Inspection.weather,
    Hydro_Inspection.notes,
    Hydro_Inspection.departure_time,
    Hydro_Inspection.creator,
    Climate_Inspection.air_temp_handheld,
	Climate_Inspection.air_temp_logger,
    Climate_Inspection.climate_notes
FROM Hydro_Inspection
    FULL JOIN Climate_Inspection ON Climate_Inspection.inspection_id = Hydro_Inspection.id
WHERE Hydro_Inspection.sitename = :site
    AND Hydro_Inspection.arrival_time >= :start_time
    AND Hydro_Inspection.arrival_time <= :end_time
ORDER BY Hydro_Inspection.arrival_time ASC
