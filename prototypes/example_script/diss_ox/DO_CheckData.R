#########################################################################################
#
#  Task Name:       <- Pull DO check data
#
#  Task Purpose:    <- This code pulls the DO check and inspection data from both Survey123
#                       and 'Provisional WaterQuality.hts' for a given site and start date
#
#  Task Outputs:    <- A csv of all DO combined check and inspection data that is saved in
#                       the specified folder
#
#  Notes:           <-
#
#  Created by:      <- Hannah Marley
#  Created on:      <- 19/01/2022
#
#  Last updated:    <- Sam Irvine
#  Last updated by: <- 07/06/2023
#
#
#  Written in R version 4.1.1
#
########################################################################################



# load required libraries
library(RODBC); library(dplyr); library(DT)
library(tidyverse); library(Hilltop); library(lubridate)
library(yaml)


# --------------------------------------------------------------------------------
# --- Define site, start date, and folder file path to save inspection data to ---
# --------------------------------------------------------------------------------
config_yaml = yaml.load_file("./DO_config.yaml")
site = config_yaml$site

startDate = as.Date(config_yaml$from_date)-1  # choose one day before your batch start date
if (is.null(config_yaml$to_date)) {
  config_yaml$to_date = format(Sys.time(), "%Y-%m-%d %H:%M:%S")
}
endDate = as.Date(config_yaml$to_date)+1  # choose one day after your batch end date
folder_filepath = "./" # here
# -----------------------------------------------------



# --- Retrieve check & inspection data from Survey123 ---

# Connect to Survey123
ch <- odbcDriverConnect('driver={SQL Server};server=DBSurvey123Live.horizons.govt.nz;database=survey123;trusted_connection=true')


# Get inspection info
inspections_Survey123 <- sqlQuery(ch, paste0("SELECT Hydro_Inspection.id, Hydro_Inspection.arrival_time, Hydro_Inspection.sitename,
                                             Hydro_Inspection.weather, Hydro_Inspection.notes,
                                             Hydro_Inspection.departure_time, Hydro_Inspection.creator,
                                             DO_Inspection.inspection_id, DO_Inspection.handheld_percent, DO_Inspection.logger_percent,
                                             DO_Inspection.handheld_concentration, DO_Inspection.handheld_baro,
                                             DO_Inspection.do_notes, DO_Inspection.inspection_id,
                                             WaterLevel_Inspection.inspection_id,
                                             WaterLevel_Inspection.wl_notes,
                                             WaterTemp_Inspection.inspection_id, WaterTemp_Inspection.wt_device,
                                             WaterTemp_Inspection.handheld_temp, WaterTemp_Inspection.logger_temp
                                             FROM [dbo].Hydro_Inspection
                                             FULL JOIN [dbo].DO_Inspection ON DO_Inspection.inspection_id = Hydro_Inspection.id
                                             FULL JOIN [dbo].WaterLevel_Inspection ON WaterLevel_Inspection.inspection_id = Hydro_Inspection.id
                                             FULL JOIN [dbo].WaterTemp_Inspection ON WaterTemp_Inspection.inspection_id = Hydro_Inspection.id
                                             WHERE Hydro_Inspection.sitename = '", site, "'
                                             AND Hydro_Inspection.arrival_time >= '", startDate, "'"),
                                  stringsAsFactors = F)


close(ch)



# Format data
Inspections = inspections_Survey123 %>%
  select(id, sitename, arrival_time, departure_time, creator, weather,
         notes, wl_notes, wt_device, do_notes,
         handheld_percent, logger_percent, handheld_concentration
  ) %>%
  mutate(arrival_time = round_date(arrival_time, "15 minutes"),
         Date = as.Date(as.character(arrival_time)),
         Time = format(arrival_time, "%H:%M:%S"))

colnames(Inspections) = c("ID", "Site Name", "Arrival Time", "Departure Time", "InspectionStaff",
                          "Weather", "Notes", "Water level notes", "MeterID", "DO Notes",
                          "Value", "Logger",
                          "DO_ug/L Handheld", "Date", "Time")

Inspections = Inspections %>%
  select("ID", "Site Name", "Date", "Time", "Weather",
         "Arrival Time", "Departure Time", "InspectionStaff",
         "Notes", "Water level notes", "MeterID", "DO Notes",
         "Value", "Logger",
         "DO_ug/L Handheld") %>%
  mutate(`Arrival Time` = as.character(`Arrival Time`),
         `Departure Time` = as.character(`Departure Time`)) %>%
  unique(.)





# --- Retrieve check & inspection data from Provisional WQ ---

# data source
dat = HilltopData("//ares/Environmental Archive/Provisional WaterQuality.hts")
meas = "Field DO Saturation (HRC) [Field DO Saturation (HRC)]"
meas1 = "Field DO Concentration (HRC) [Field DO Concentration (HRC)]"
#(measurements = MeasurementList(dat, site))

# Get the data from Hilltop
provisWQ_dat1 = GetData(dat, site, meas1, startDate, "")
provisWQ_dat1 = fortify.zoo(provisWQ_dat1, melt = FALSE)
provisWQ_dat1 = provisWQ_dat1 %>%
  rename("DO_ug/L Handheld" = "provisWQ_dat1")


provisWQ_dat = GetData(dat, site, meas, startDate, "", WQParams = TRUE)
provisWQ_dat = fortify.zoo(provisWQ_dat, melt = FALSE)



# --- Join all data together and format ---

full_dat = provisWQ_dat %>%
  full_join(., provisWQ_dat1, by = "Index") %>%
  mutate(Index = round_date(Index, "15 minutes"),
         "Arrival Time" = as.character(Index),
         Date = as.Date(Index),
         Time = format(Index, "%H:%M:%S"),
         ID = NA,
         `Site Name` = site,
         `Departure Time` = NA,
         `Water level notes` = NA,
         `DO Notes` = NA,
         `DO% Logger` = NA) %>%
  rename("Value" = "Field DO Saturation (HRC)",
         "Logger" = "DO% Logger",
         "InspectionStaff" = "SampledBy",
         "Notes" = "Comments") %>%
  select(ID, `Site Name`, Date, Time, Weather, `Arrival Time`, `Departure Time`,
         InspectionStaff, Notes, `Water level notes`, MeterID,
         `DO Notes`, `DO_ug/L Handheld`,
         `Value`, `Logger`) %>%
  rbind(., Inspections) %>%
  select(-ID) %>%
  arrange(desc(`Arrival Time`))



# --- save to csv ---
write.csv(full_dat, paste0(folder_filepath, "DO_Inspections.csv"), row.names = FALSE)





# ------ Pull non-conformances for sites ------

# Connect to survey123 sql table
ch = odbcDriverConnect('driver={SQL Server};server=sql3dev.horizons.govt.nz;database=survey123;trusted_connection=true')

NCR = sqlQuery(ch, paste0("SELECT Hydro_Inspection.id, Hydro_Inspection.sitename,
                                             Non_Conformances.*
                                             FROM [dbo].Non_Conformances
                                             INNER JOIN Hydro_Inspection ON Non_Conformances.inspection_id = Hydro_Inspection.id
                                             WHERE Hydro_Inspection.sitename = '", site, "'"),
               stringsAsFactors = F)

close(ch)


# Connect to logsheets
ch1 = odbcConnectAccess2007("//ares/HydrologySoftware/Catchment Data Tools/CDT4.accdb")

NCRs = sqlQuery(ch1, paste0("SELECT NonConformance.* FROM NonConformance WHERE NonConformance.Sitename= '", site, "'"),
                stringsAsFactors = F)

close(ch1)



NCR_survey123 = NCR %>%
  mutate(created_date = as.character(created_date),
         edit_date = as.character(edit_date)) %>%
  select(sitename, created_date, creator, edit_date, summary, missing_record, days_missing_record, corrective_action) %>%
  rename("Sitename" = "sitename",
         "Entrydate" = "created_date",
         "Reportby" = "creator",
         "ReportDate" = "edit_date",
         "NC_Summary" = "summary",
         "MissingRecord" = "missing_record",
         "MissingRecord_Days" = "days_missing_record",
         "CorrectiveAction" = "corrective_action")


NCRs = NCRs %>%
  mutate(Entrydate = as.character(Entrydate),
         ReportDate = as.character(ReportDate)) %>%
  select(Sitename, Entrydate, Reportby, ReportDate, NC_Summary, MissingRecord, MissingRecord_Days, CorrectiveAction)

NCRs = NCRs %>%
  rbind(., NCR_survey123) %>%
  mutate(Date = as.Date(ReportDate)) %>%
  arrange(Date) %>%
  select(-Date) %>%
  filter(as.Date(ReportDate) >= startDate,
         as.Date(ReportDate) <= endDate)

write.csv(NCRs, paste0(folder_filepath, "DO_non-conformance_reports.csv"), row.names = FALSE)





# ------ Keep just check data, format to fit Hilltop and save as csv ------

check_data = full_dat %>%
  select(Date, Time, `DO_ug/L Handheld`, `Value`, `Arrival Time`, Notes) %>%
  filter(!is.na(`Value`),
         Date <= endDate) %>%
  distinct(Date, `DO_ug/L Handheld`, .keep_all = TRUE) %>%
  rename("DO saturation check" = "Value",
         "Recorder Time" = "Arrival Time",
         "Comment" = "Notes") %>%
  mutate(`DO saturation check` = as.numeric(`DO saturation check`)) %>%
  mutate(`Comment` = gsub("\r?\n|\r", " ", `Comment`)) %>%
  select(Date, Time, `DO saturation check`, `Recorder Time`, Comment) %>%
  arrange(`Recorder Time`)


write.csv(check_data, paste0(folder_filepath, "DO_check_data.csv"), row.names = FALSE)

#Same thing as check data, but includes non-measurement inspections for visual data inspection
working_check_data = full_dat %>%
  select(Date, Time, `DO_ug/L Handheld`, `Value`, `Arrival Time`, Notes) %>%
  filter(Date <= endDate) %>%
  distinct(Date, `DO_ug/L Handheld`, .keep_all = TRUE) %>%
  rename("DO saturation check" = "Value",
         "Recorder Time" = "Arrival Time",
         "Comment" = "Notes") %>%
  mutate(`DO saturation check` = as.numeric(`DO saturation check`)) %>%
  mutate(`Comment` = gsub("\r?\n|\r", " ", `Comment`)) %>%
  select(Date, Time, `DO saturation check`, `Recorder Time`, Comment) %>%
  arrange(`Recorder Time`)


write.csv(working_check_data, paste0(folder_filepath, "DO_working_check_data.csv"), row.names = FALSE)



rm(list = ls())
