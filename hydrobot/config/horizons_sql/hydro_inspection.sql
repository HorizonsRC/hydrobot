SELECT Hydro_Inspection.arrival_time,
    Hydro_Inspection.departure_time,
    Hydro_Inspection.creator,
    Hydro_Inspection.weather,
    Hydro_Inspection.notes
FROM [dbo].Hydro_Inspection
WHERE Hydro_Inspection.arrival_time >= :start_time
    AND Hydro_Inspection.arrival_time < :end_time
    AND Hydro_Inspection.sitename = :site
ORDER BY Hydro_Inspection.arrival_time ASC
