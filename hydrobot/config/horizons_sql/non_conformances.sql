SELECT Hydro_Inspection.id AS inspection_id
    ,Non_Conformances.[id] AS non_con_id
    ,[type]
    ,[summary]
    ,[resolved]
    ,[corrective_action]
    ,[completed_onsite]
    ,[date_opened]
    ,[missing_record]
    ,[days_missing_record]
    ,[datasources_affected]
    ,[created_date]
    ,Non_Conformances.[edit_date]
    ,Non_Conformances.[creator]
FROM [dbo].Non_Conformances
INNER JOIN Hydro_Inspection ON Non_Conformances.inspection_id = Hydro_Inspection.id
WHERE Hydro_Inspection.sitename = :site;
