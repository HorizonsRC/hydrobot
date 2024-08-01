"""Rainfall Processor Class."""

import warnings

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from annalist.annalist import Annalist
from annalist.decorators import ClassLogger

import hydrobot.measurement_specific_functions.rainfall as rf
from hydrobot import plotter
from hydrobot.processor import Processor, evaluator, utils

annalizer = Annalist()


class RFProcessor(Processor):
    """Processor class specifically for Rainfall."""

    def __init__(
        self,
        base_url: str,
        site: str,
        standard_hts: str,
        standard_measurement_name: str,
        frequency: str,
        from_date: str | None = None,
        to_date: str | None = None,
        check_hts: str | None = None,
        check_measurement_name: str | None = None,
        defaults: dict | None = None,
        interval_dict: dict | None = None,
        constant_check_shift: float = 0,
        **kwargs,
    ):
        super().__init__(
            base_url=base_url,
            site=site,
            standard_hts=standard_hts,
            standard_measurement_name=standard_measurement_name,
            frequency=frequency,
            from_date=from_date,
            to_date=to_date,
            check_hts=check_hts,
            check_measurement_name=check_measurement_name,
            defaults=defaults,
            interval_dict=interval_dict,
            constant_check_shift=constant_check_shift,
            **kwargs,
        )
        self.ramped_standard = None

    @ClassLogger
    def quality_encoder(
        self,
        gap_limit: int | None = None,
        max_qc: int | float | None = None,
        supplemental_data: pd.Series | None = None,
    ):
        """
        Encode quality information in the quality series for a rainfall dataset.

        Also makes ramped_standard dataset.

        Parameters
        ----------
        gap_limit : int or None, optional
            The maximum number of consecutive missing values to consider as gaps, by
            default None.
            If None, the gap limit from the class defaults is used.
        max_qc : numeric or None, optional
            Maximum quality code possible at site
            If None, the max qc from the class defaults is used.
        supplemental_data : pd.Series or None, optional
            Used for checking if data is missing. Another source of data can be
            used to find any gaps in periods where no rainfall is collected,
            and it is unclear whether the SCADA meter is inactive or the
            weather is just dry.

        Returns
        -------
        None

        Notes
        -----
        This method encodes quality information in the quality series based on the
        provided standard series, check series, and measurement information. It uses
        the evaluator.quality_encoder function to determine the quality flags for the
        data.

        Examples
        --------
        >>> processor = Processor(base_url="https://hilltop-server.com", site="Site1")
        >>> processor.quality_encoder(gap_limit=5)
        >>> processor.quality_data["Value"]
        <updated quality series with encoded quality flags>
        """
        # Filling empty values with default values
        if gap_limit is None:
            gap_limit = (
                int(self._defaults["gap_limit"])
                if "gap_limit" in self._defaults
                else None
            )
        if max_qc is None:
            max_qc = self._defaults["max_qc"] if "max_qc" in self._defaults else np.NaN

        # Select all check data values that are marked to be used for QC purposes
        checks_for_qcing = self.check_data[self.check_data["QC"]]

        # If no check data, set to empty series
        checks_for_qcing = (
            checks_for_qcing["Value"] if "Value" in checks_for_qcing else pd.Series({})
        )

        # Round all checks to the nearest 6min
        checks_for_qcing = utils.series_rounder(checks_for_qcing)

        start_date = pd.to_datetime(self.from_date)

        # If the start date is not a date stamp in the standard data set, insert a zero
        if start_date not in self.standard_data.index:
            self.standard_data = pd.concat(
                [
                    pd.DataFrame(
                        [[0.0, 0.0, "SRT", "Starting date added for ramping"]],
                        index=[start_date],
                        columns=self.standard_data.columns,
                    ),
                    self.standard_data,
                ]
            )

        # Repack the standard data to 6 minute interval
        six_minute_data = utils.rainfall_six_minute_repacker(
            self.standard_data["Value"]
        )

        # Ramp standard data to go through the check data points
        ramped_standard, deviation_points = utils.check_data_ramp_and_quality(
            six_minute_data, checks_for_qcing
        )

        time_points = rf.rainfall_time_since_inspection_points(checks_for_qcing)

        (
            site_survey_points,
            three_point_sum,
            comment,
            output_dict,
        ) = rf.rainfall_nems_site_matrix(self.site)

        quality_series = rf.points_to_qc(
            [deviation_points, time_points], site_survey_points, three_point_sum
        )

        self.ramped_standard = ramped_standard
        qc_frame = quality_series.to_frame(name="Value")
        qc_frame["Code"] = "RFL"
        qc_frame["Details"] = "Rainfall custom quality encoding"
        self._apply_quality(qc_frame, replace=True)

        if supplemental_data is not None:
            msg_frame = evaluator.missing_data_quality_code(
                supplemental_data,
                self.quality_data,
                gap_limit=gap_limit,
            )
            self._apply_quality(msg_frame)
        else:
            warnings.warn(
                "MISSING SUPPLEMENTAL PARAMETER: Rainfall needs a supplemental"
                " data source to detect missing data.",
                stacklevel=1,
            )

        lim_frame = evaluator.max_qc_limiter(self.quality_data, max_qc)
        self._apply_quality(lim_frame)

    @property  # type: ignore
    def cumulative_standard_data(self) -> pd.DataFrame:  # type: ignore
        """pd.Series: The standard series data."""
        data = self._standard_data.copy()
        data["Raw"] = data["Raw"].cumsum()
        data["Value"] = data["Value"].cumsum()
        return data

    @property  # type: ignore
    def cumulative_check_data(self) -> pd.DataFrame:  # type: ignore
        """pd.Series: The check series data."""
        data = self._check_data.copy()
        data["Raw"] = data["Raw"].cumsum()
        data["Value"] = data["Value"].cumsum()
        return data

    def plot_qc_series(self, check=False, show=True):
        """Implement qc_plotter()."""
        fig = plotter.qc_plotter_plotly(
            self._standard_data["Value"],
            (self._check_data["Value"] if check else None),
            self._quality_data["Value"],
            show=show,
        )

        fig.add_trace(
            go.Scatter(
                x=self.ramped_standard.index,
                y=self.ramped_standard.cumsum(),
                mode="lines",
                name="Ramped",
                line=dict(color="#1010F0", dash="dot"),
            )
        )
        return fig

    def filter_manual_tips(self, check_query: pd.DataFrame):
        """
        Attempts to remove manual tips from standard_series.

        Parameters
        ----------
        check_query : pd.DataFrame
            The DataFrame of all the checks that have been done

        Returns
        -------
        None, self.standard_data modified
        """
        for _, check in check_query.iterrows():
            self.standard_data["Value"], issue = rf.manual_tip_filter(
                self.standard_data["Value"],
                check["start_time"],
                check["end_time"],
                check["primary_manual_tips"],
            )
            if issue is not None:
                self.report_processing_issue(**issue)
