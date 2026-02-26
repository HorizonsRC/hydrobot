"""Dissolved Oxygen Processor Class."""

import re

import numpy as np
import pandas as pd
from annalist.decorators import ClassLogger
from hilltoppy import Hilltop

import hydrobot.config.horizons_source as source
from hydrobot import data_sources
from hydrobot.data_acquisition import enforce_site_in_hts
from hydrobot.evaluator import cap_qc_where_std_high
from hydrobot.filters import trim_series
from hydrobot.measurement_specific_functions.dissolved_oxygen import (
    correct_dissolved_oxygen,
)
from hydrobot.processor import (
    EMPTY_QUALITY_DATA,
    EMPTY_STANDARD_DATA,
    Processor,
)
from hydrobot.utils import compare_two_qc_take_min


class DOProcessor(Processor):
    """Processor class specifically for Dissolved Oxygen."""

    def __init__(
        self,
        base_url: str,
        site: str,
        standard_hts_filename: str,
        standard_measurement_name: str,
        frequency: str | None,
        water_temperature_site: str | None,
        atmospheric_pressure_site: str | None,
        water_temperature_hts: str | None,
        atmospheric_pressure_hts: str | None,
        atmospheric_pressure_frequency: str,
        water_temperature_frequency: str,
        atmospheric_pressure_site_altitude: float | None,
        site_altitude: float | None = None,
        water_temperature_measurement_name: str | None = "Water Temperature",
        atmospheric_pressure_measurement_name: str | None = "Atmospheric Pressure",
        from_date: str | None = None,
        to_date: str | None = None,
        check_hts_filename: str | None = None,
        check_measurement_name: str | None = None,
        defaults: dict | None = None,
        interval_dict: dict | None = None,
        constant_check_shift: float = 0,
        fetch_quality: bool = False,
        export_file_name: str | None = None,
        **kwargs,
    ):
        super().__init__(
            base_url=base_url,
            site=site,
            standard_hts_filename=standard_hts_filename,
            standard_measurement_name=standard_measurement_name,
            frequency=frequency,
            from_date=from_date,
            to_date=to_date,
            check_hts_filename=check_hts_filename,
            check_measurement_name=check_measurement_name,
            defaults=defaults,
            interval_dict=interval_dict,
            constant_check_shift=constant_check_shift,
            fetch_quality=fetch_quality,
            export_file_name=export_file_name,
            **kwargs,
        )
        if water_temperature_site is None:
            self.water_temperature_site = self.site
        else:
            self.water_temperature_site = water_temperature_site
        if atmospheric_pressure_site is None:
            self.atmospheric_pressure_site = source.site_info_lookup(self.site)[
                "BARO_CLOSEST"
            ]
        else:
            self.atmospheric_pressure_site = atmospheric_pressure_site

        wt_hilltop = Hilltop(base_url, water_temperature_hts)
        ap_hilltop = Hilltop(base_url, atmospheric_pressure_hts)

        enforce_site_in_hts(wt_hilltop, self.water_temperature_site)
        if self.water_temperature_site not in wt_hilltop.available_sites:
            raise ValueError(
                f"Water Temperature site '{self.water_temperature_site}' not found for both base_url and hts combos."
                f"Available sites in {water_temperature_hts} are: "
                f"{[s for s in wt_hilltop.available_sites]}"
            )

        if self.atmospheric_pressure_site not in ap_hilltop.available_sites:
            raise ValueError(
                f"Atmospheric Pressure site '{self.atmospheric_pressure_site}' not found for both base_url and hts combos."
                f"Available sites in {atmospheric_pressure_hts} are: "
                f"{[s for s in ap_hilltop.available_sites]}"
            )

        # Atmospheric Pressure
        available_ap_measurements = ap_hilltop.get_measurement_list(
            atmospheric_pressure_site
        )
        self.atmospheric_pressure_measurement_name = (
            atmospheric_pressure_measurement_name
        )
        matches = re.search(
            r"([^\[\n]+)(\[(.+)\])?", atmospheric_pressure_measurement_name
        )

        if matches is not None:
            self.ap_item_name = matches.groups()[0].strip(" ")
            self.ap_data_source_name = matches.groups()[2]
            if self.ap_data_source_name is None:
                self.ap_data_source_name = self.ap_item_name
        if atmospheric_pressure_measurement_name not in list(
            available_ap_measurements.MeasurementName
        ):
            raise ValueError(
                "Atmospheric pressure measurement name "
                f"'{atmospheric_pressure_measurement_name}' not found at"
                f" site '{site}'. "
                "Available measurements are "
                f"{list(available_ap_measurements.MeasurementName)}"
            )

        # Water Temperature
        available_wt_measurements = wt_hilltop.get_measurement_list(
            water_temperature_site
        )
        if self.depth is None:
            self.water_temperature_measurement_name = water_temperature_measurement_name
        else:
            self.water_temperature_measurement_name = (
                data_sources.depth_standard_measurement_name_by_data_family(
                    "water_temperature", self.depth
                )
            )
        matches = re.search(
            r"([^\[\n]+)(\[(.+)\])?", self.water_temperature_measurement_name
        )

        if matches is not None:
            self.wt_item_name = matches.groups()[0].strip(" ")
            self.wt_data_source_name = matches.groups()[2]
            if self.wt_data_source_name is None:
                self.wt_data_source_name = self.wt_item_name
        if water_temperature_measurement_name not in list(
            available_wt_measurements.MeasurementName
        ):
            raise ValueError(
                "Water temperature measurement name "
                f"'{water_temperature_measurement_name}' not found at"
                f" site '{site}'. "
                "Available measurements are "
                f"{list(available_wt_measurements.MeasurementName)}"
            )

        self.water_temperature_hts = water_temperature_hts
        self.atmospheric_pressure_hts = atmospheric_pressure_hts

        self.water_temperature_frequency = water_temperature_frequency
        self.atmospheric_pressure_frequency = atmospheric_pressure_frequency

        if site_altitude is None:
            self.site_altitude = float(source.site_info_lookup(self.site)["BARO_RL"])
        else:
            self.site_altitude = site_altitude

        if atmospheric_pressure_site_altitude is None:
            self.atmospheric_pressure_site_altitude = float(
                source.site_info_lookup(self.site)["BARO_CLOSEST_RL"]
            )
        else:
            self.atmospheric_pressure_site_altitude = atmospheric_pressure_site_altitude

        self.ap_standard_item_info = {
            "item_name": self.ap_item_name,
            "item_format": "F",
            "divisor": 1,
            "units": "",
            "number_format": "###.##",
        }
        self.wt_standard_item_info = {
            "item_name": self.wt_item_name,
            "item_format": "F",
            "divisor": 1,
            "units": "",
            "number_format": "###.##",
        }

        self.ap_standard_data = EMPTY_STANDARD_DATA.copy()
        self.ap_quality_data = EMPTY_QUALITY_DATA.copy()

        self.wt_standard_data = EMPTY_STANDARD_DATA.copy()
        self.wt_quality_data = EMPTY_QUALITY_DATA.copy()

        self.ap_standard_data = self.import_standard(
            standard_hts_filename=self.atmospheric_pressure_hts,
            site=self.atmospheric_pressure_site,
            standard_measurement_name=self.atmospheric_pressure_measurement_name,
            standard_data_source_name=self.ap_data_source_name,
            standard_item_info=self.standard_item_info,
            standard_data=self.ap_standard_data,
            from_date=self.from_date,
            to_date=self.to_date,
            frequency=self.atmospheric_pressure_frequency,
            infer_frequency=False,
        )
        self.wt_standard_data = self.import_standard(
            standard_hts_filename=self.water_temperature_hts,
            site=self.water_temperature_site,
            standard_measurement_name=self.water_temperature_measurement_name,
            standard_data_source_name=self.wt_data_source_name,
            standard_item_info=self.standard_item_info,
            standard_data=self.wt_standard_data,
            from_date=self.from_date,
            to_date=self.to_date,
            frequency=self.water_temperature_frequency,
            infer_frequency=False,
        )
        if self.ap_standard_data.empty or self.wt_standard_data.empty:
            raise ValueError(
                f"DO processing requires WT and AP data, but WT missing: {self.wt_standard_data.empty}, "
                f"AP missing: {self.ap_standard_data.empty}."
            )

        ap_last_time = self.ap_standard_data.index[-1]
        wt_last_time = self.wt_standard_data.index[-1]
        if self._to_date > min([ap_last_time, wt_last_time]):
            self.report_processing_issue(
                start_time=self.to_date,
                end_time=min([ap_last_time, wt_last_time]),
                comment="Changing to_date to end of AP/WT processing.",
                message_type="info",
            )
            self._to_date = min([ap_last_time, wt_last_time, self._to_date])
        self.wt_standard_data = self.wt_standard_data.reindex(
            self.standard_data[self.standard_data.index <= wt_last_time].index,
            method="nearest",
        )
        self.ap_standard_data = self.ap_standard_data.reindex(
            self.standard_data[self.standard_data.index <= ap_last_time].index,
            method="nearest",
        )
        self.standard_data["Value"] = trim_series(
            self.standard_data["Value"], min([ap_last_time, wt_last_time])
        )
        self.check_data["Value"] = trim_series(
            self.check_data["Value"], min([ap_last_time, wt_last_time])
        )

        self.wt_quality_data = self.import_quality(
            standard_hts_filename=self.water_temperature_hts,
            site=self.water_temperature_site,
            standard_measurement_name=self.water_temperature_measurement_name,
            standard_data_source_name=self.wt_data_source_name,
            quality_data=self.wt_quality_data,
            from_date=self.from_date,
            to_date=self.to_date,
        )
        self.ap_quality_data = self.import_quality(
            standard_hts_filename=self.atmospheric_pressure_hts,
            site=self.atmospheric_pressure_site,
            standard_measurement_name=self.atmospheric_pressure_measurement_name,
            standard_data_source_name=self.ap_data_source_name,
            quality_data=self.ap_quality_data,
            from_date=self.from_date,
            to_date=self.to_date,
        )

    @ClassLogger
    def correct_do(
        self, diss_ox=None, atm_pres=None, ap_altitude=None, do_altitude=None
    ):
        """
        Correcting for atmospheric pressure.

        Parameters
        ----------
        diss_ox
        atm_pres
        ap_altitude
        do_altitude

        Returns
        -------
        None, modifies standard_data
        """
        if diss_ox is None:
            diss_ox = self.standard_data
        if atm_pres is None:
            atm_pres = self.ap_standard_data
        if ap_altitude is None:
            ap_altitude = self.atmospheric_pressure_site_altitude
        if do_altitude is None:
            do_altitude = self.site_altitude

        self.standard_data["Value"] = correct_dissolved_oxygen(
            diss_ox["Value"], atm_pres["Value"], ap_altitude, do_altitude
        )

    @ClassLogger
    def quality_encoder(
        self,
        gap_limit: int | None = None,
        max_qc: int | float | None = None,
        interval_dict: dict | None = None,
    ):
        """
        DO version of quality encoder.

        Parameters
        ----------
        gap_limit
        max_qc
        interval_dict

        Returns
        -------
        None
        """
        super().quality_encoder(
            gap_limit=gap_limit, max_qc=max_qc, interval_dict=interval_dict
        )

        # Atmospheric Pressure
        qc_frame = self.quality_data
        qc_data = compare_two_qc_take_min(
            self.quality_data["Value"], self.ap_quality_data["Value"]
        )

        with pd.option_context("future.no_silent_downcasting", True):
            qc_frame = qc_frame.reindex(qc_data.index, method="ffill").infer_objects(
                copy=False
            )

        diff_idxs = qc_frame[qc_frame["Value"] != qc_data].index

        qc_frame.loc[diff_idxs, "Code"] = "APD"
        qc_frame.loc[diff_idxs, "Details"] = (
            qc_frame.loc[diff_idxs, "Details"] + " [DO QC lowered by AP QC]"
        )
        qc_frame["Value"] = qc_data
        self.quality_data = qc_frame

        # Water temperature
        qc_frame = self.quality_data
        qc_data = compare_two_qc_take_min(
            self.quality_data["Value"], self.wt_quality_data["Value"]
        )

        with pd.option_context("future.no_silent_downcasting", True):
            qc_frame = qc_frame.reindex(qc_data.index, method="ffill").infer_objects(
                copy=False
            )

        diff_idxs = qc_frame[qc_frame["Value"] != qc_data].index

        qc_frame.loc[diff_idxs, "Code"] = "WTD"
        qc_frame.loc[diff_idxs, "Details"] = (
            qc_frame.loc[diff_idxs, "Details"] + " [DO QC lowered by WT QC]"
        )
        qc_frame["Value"] = qc_data
        self.quality_data = qc_frame

        # DO above 100
        cap_frame = cap_qc_where_std_high(
            self.standard_data, self.quality_data, 500, 100
        )
        self.quality_data = cap_frame
        # self._apply_quality(cap_frame)
        if self.quality_data["Value"].iloc[-1] == 100:
            self.quality_data.loc[self.to_date, "Value"] = 0

    @staticmethod
    def _keys_to_be_set_to_none_if_missing():
        keys = [
            "frequency",
            "water_temperature_site",
            "atmospheric_pressure_site",
            "water_temperature_hts",
            "atmospheric_pressure_hts",
            "atmospheric_pressure_site_altitude",
            "water_temperature_measurement_name",
            "atmospheric_pressure_measurement_name",
            "check_hts_filename",
            "check_measurement_name",
        ]
        return keys

    def remove_qc100_data(self):
        """For when WT is QC100and making standard data qc100."""
        starts_of_qc100_data = self.quality_data.index[
            self.quality_data["Value"] == 100
        ]
        ends_of_qc100_data = self.quality_data.index[
            self.quality_data.shift()["Value"] == 100
        ]
        for qc100_section in zip(starts_of_qc100_data, ends_of_qc100_data, strict=True):
            self.standard_data.loc[
                (self.standard_data.index > qc100_section[0])
                & (self.standard_data.index < qc100_section[1]),
                "Value",
            ] = np.nan
