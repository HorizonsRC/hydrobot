#########################################################################################
#
#  Task Name:       <- Pull Atmospheric Pressure check data
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
#  Created on:      <- 02/12/2022
#
#  Last updated:    <- 05/03/2024
#  Last updated by: <- Nic
#
#
#  Written in R version 4.1.1
#
########################################################################################

# Make sure the script is working in the right place
setwd(dirname(rstudioapi::getActiveDocumentContext()$path))
# setwd(getSrcDirectory(function(){})[1]) # might need to use this if it's run as a script

# load required libraries
library(RODBC); library(dplyr); library(DT)
library(tidyverse); library(Hilltop); library(lubridate)
library(yaml)

# --------------------------------------------------------------------------------
# --- Define site, start date, and folder file path to save inspection data to ---
# --------------------------------------------------------------------------------
config_yaml = yaml.load_file("./config.yaml")
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
                                             DO_Inspection.inspection_id, DO_Inspection.handheld_baro, DO_Inspection.logger_baro,
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
         handheld_baro, logger_baro
  ) %>%
  mutate(arrival_time = round_date(arrival_time, "15 minutes"),
         Date = as.Date(as.character(arrival_time)),
         Time = format(arrival_time, "%H:%M:%S"))

colnames(Inspections) = c("ID", "Site Name", "Arrival Time", "Departure Time", "InspectionStaff",
                          "Weather", "Notes", "Water level notes", "MeterID", "DO Notes",
                          "Value", "Logger",
                          "Date", "Time")

Inspections = Inspections %>%
  select("ID", "Site Name", "Date", "Time", "Weather",
         "Arrival Time", "Departure Time", "InspectionStaff",
         "Notes", "Water level notes", "MeterID", "DO Notes",
         "Value", "Logger") %>%
  mutate(`Arrival Time` = as.character(`Arrival Time`),
         `Departure Time` = as.character(`Departure Time`)) %>%
  unique(.)

write.csv(Inspections, paste0(folder_filepath, "AP_Inspections.csv"), row.names = FALSE)



# --- Retrieve check & inspection data from Provisional WQ ---

# data source
dat = HilltopData("//ares/Environmental Archive/Provisional WaterQuality.hts")
meas = "Field Baro Pressure (HRC) [Field Baro Pressure (HRC)]"
#(measurements = MeasurementList(dat, site))
sites = SiteList(dat)

if (site %in% sites){

  # Get the data from Hilltop
  provisWQ_dat = GetData(dat, site, meas, startDate, "", WQParams = TRUE)
  provisWQ_dat = fortify.zoo(provisWQ_dat, melt = FALSE)

  provisWQ_dat = provisWQ_dat %>%
     mutate(Index = round_date(Index, "15 minutes"),
            "Arrival Time" = as.character(Index),
            Date = as.Date(Index),
            Time = format(Index, "%H:%M:%S"),
            ID = NA,
            `Site Name` = site,
            `Departure Time` = NA,
            `Water level notes` = NA,
            `DO Notes` = NA,
            `Logger` = NA) %>%
     rename("Value" = "Field Baro Pressure (HRC)",
            "InspectionStaff" = "SampledBy",
            "Notes" = "Comments") %>%
     select(ID, `Site Name`, Date, Time, Weather, `Arrival Time`, `Departure Time`,
            InspectionStaff, Notes, `Water level notes`, MeterID,
            `DO Notes`, `Value`,
            `Logger`) %>%
  #   rbind(., Inspections) %>%
  #   select(-ID) %>%
     arrange(desc(`Arrival Time`))
  # --- save to csv ---
  write.csv(provisWQ_dat, paste0(folder_filepath, "AP_ProvWQ.csv"), row.names = FALSE)
  full_dat = provisWQ_dat %>%
    rbind(., Inspections) %>%
    select(-ID) %>%
    arrange(desc(`Arrival Time`))
} else {
 full_dat = Inspections
}







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

write.csv(NCRs, paste0(folder_filepath, "AP_non-conformance_reports.csv"), row.names = FALSE)





# ------ Keep just check data, format to fit Hilltop and save as csv ------

check_data = full_dat %>%
  select(Date, Time, `Value`, `Arrival Time`, Notes) %>%
  filter(!is.na(`Value`),
         Date <= endDate) %>%
  distinct(Date, `Value`, .keep_all = TRUE) %>%
  dplyr::rename("Check Pressure" = "Value",
         "Recorder Time" = "Arrival Time",
        "Comment" = "Notes") %>%
  mutate(`Check Pressure` = as.numeric(`Check Pressure`)) %>%
  #select(Date, Time, `Check Pressure`, `Recorder Time`, Comment) %>%
  arrange(`Recorder Time`)

# Escape newlines
check_data$Comment = gsub("\r?\n|\r", "---NEWLINE---",check_data$Comment)

write.csv(check_data,
          paste0(folder_filepath,
                 paste0("AP_check_data_", gsub("-", "", Sys.Date()), ".csv")),
          row.names = FALSE)



rm(list = ls())
