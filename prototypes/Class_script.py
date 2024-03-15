"""Script to run through a processing task with the processor class."""

import matplotlib.pyplot as plt
import pandas as pd
from annalist.annalist import Annalist
import plotly.graph_objects as go

from hydrobot.processor import Processor

processing_parameters = {
    "base_url": "http://hilltopdev.horizons.govt.nz/",
    "standard_hts_filename": "RawLoggerNet.hts",
    "check_hts_filename": "boo.hts",
    "site": "Hautapu at Alabasters",
    "from_date": "2021-12-02 11:00",
    "to_date": "2024-01-10 11:00",
    "frequency": "15min",
    "standard_measurement_name": "Water Temperature",
    "check_measurement_name": "Water Temperature Check [Water Temperature]",
    "defaults": {
        "high_clip": 30,
        "low_clip": 0,
        "delta": 5,
        "span": 10,
        "gap_limit": 12,
        "max_qc": 600,
    },
}

ann = Annalist()
stream_format_str = (
    "%(asctime)s, %(analyst_name)s, %(function_name)s, %(site)s, "
    "%(measurement)s, %(from_date)s, %(to_date)s, %(message)s"
)
ann.configure(
    logfile="bot_annals.csv",
    analyst_name="Slam Slurvine",
    stream_format_str=stream_format_str,
)

data = Processor(
    processing_parameters["base_url"],
    processing_parameters["site"],
    processing_parameters["standard_hts_filename"],
    processing_parameters["standard_measurement_name"],
    processing_parameters["frequency"],
    processing_parameters["from_date"],
    processing_parameters["to_date"],
    processing_parameters["check_hts_filename"],
    processing_parameters["check_measurement_name"],
    processing_parameters["defaults"],
)

raw_data = data.raw_standard_series
data.clip()


# data.remove_flatlined_values()
data.remove_spikes()
# data.delete_range("2021-06-29 11:00", "2021-06-30 11:25")
data.insert_missing_nans()

data.gap_closer()
data.quality_encoder()

data.data_exporter("processed.xml")

def import_check_data():
    df = pd.read_csv("WaterTemp_check_data.csv")
    if not df.empty:
        df["Datetime"] = pd.to_datetime(df['Date'] + " " + df["Time"])
        df.set_index('Datetime', inplace=True)
        df.drop(columns=["Date", "Time"], inplace=True)
    return df

def import_inspections():
    df = pd.read_csv("WaterTemp_Inspections.csv")
    if not df.empty:
        df["Datetime"] = pd.to_datetime(df['Date'] + " " + df["Time"])
        df.set_index('Datetime', inplace=True)
        df.drop(columns=["Date", "Time"], inplace=True)
    return df

def import_ncr():
    df = pd.read_csv("WaterTemp_non-conformance_reports.csv")
    if not df.empty:
        df["Datetime"] = pd.to_datetime(df['Date'] + " " + df["Time"])
        df.set_index('Datetime', inplace=True)
        df.drop(columns=["Date", "Time"], inplace=True)
    return df

checks = import_check_data()
inspections = import_inspections()
ncrs = import_ncr()

print(checks)
print(inspections)
print(ncrs)

with plt.rc_context(rc={"figure.max_open_warning": 0}):
    fig = data.plot_qc_series(show=False)
    fig.add_trace(go.Scatter(
        x=checks.index,
        y=checks["Water Temperature check"],
        mode='markers',
        name="Spot Checks",
        marker=dict(color='blue', size=8, symbol='cross-dot'),
    ))
    fig.add_trace(go.Scatter(
        x=inspections.index,
        y=inspections["Temp Check"],
        mode='markers',
        name="Inspections check",
        marker=dict(color='red', size=8, symbol='square-open'),
    ))
    fig.add_trace(go.Scatter(
        x=inspections.index,
        y=inspections["Temp Logger"],
        mode='markers',
        name="Inspections Logger",
        marker=dict(color='magenta', size=8, symbol='diamond-open'),
    ))
    # data.plot_qc_series(show=false)race(go.scatter())
    # data.plot_gaps(show=False)
    # data.plot_checks(show=False)
    # plt.get_current_fig_manager().window.showMaximized()
    fig.show()
