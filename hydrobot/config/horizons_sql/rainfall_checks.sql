SELECT Hydro_Inspection.arrival_time,
    Hydro_Inspection.weather,
    Hydro_Inspection.notes,
    Hydro_Inspection.departure_time,
    Hydro_Inspection.creator,
    Rainfall_Inspection.dipstick,
    ISNULL(Rainfall_Inspection.flask, Rainfall_Inspection.dipstick) as 'check',
    Rainfall_Inspection.flask,
    Rainfall_Inspection.gauge_emptied,
    Rainfall_Inspection.primary_total,
    Manual_Tips.start_time,
    Manual_Tips.end_time,
    Manual_Tips.primary_manual_tips,
    Manual_Tips.backup_manual_tips,
    RainGauge_Validation.pass
FROM [dbo].RainGauge_Validation
    RIGHT JOIN ([dbo].Manual_Tips
        RIGHT JOIN ([dbo].Rainfall_Inspection
            INNER JOIN [dbo].Hydro_Inspection
            ON Rainfall_Inspection.inspection_id = Hydro_Inspection.id)
        ON Manual_Tips.inspection_id = Hydro_Inspection.id)
    ON RainGauge_Validation.inspection_id = Hydro_Inspection.id
WHERE Hydro_Inspection.arrival_time >= :start_time
    AND Hydro_Inspection.arrival_time < :end_time
    AND Hydro_Inspection.sitename = :site
    AND ISNULL(Rainfall_Inspection.flask, Rainfall_Inspection.dipstick) IS NOT NULL
ORDER BY Hydro_Inspection.arrival_time ASC
