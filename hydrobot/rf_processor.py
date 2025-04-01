"""Rainfall Processor Class."""

from datetime import datetime

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from annalist.annalist import Annalist
from annalist.decorators import ClassLogger

import hydrobot.measurement_specific_functions.rainfall as rf
import hydrobot.processor as processor
from hydrobot import filters, plotter
from hydrobot.processor import Processor, data_structure, evaluator, utils

annalizer = Annalist()


class RFProcessor(Processor):
    """Processor class specifically for Rainfall."""

    def __init__(
        self,
        base_url: str,
        site: str,
        standard_hts_filename: str,
        standard_measurement_name: str,
        frequency: str,
        from_date: str | None = None,
        to_date: str | None = None,
        check_hts_filename: str | None = None,
        check_measurement_name: str | None = None,
        defaults: dict | None = None,
        interval_dict: dict | None = None,
        constant_check_shift: float = 0,
        fetch_quality: bool = False,
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
            **kwargs,
        )
        self.standard_item_info = {
            "item_name": self.standard_item_name,
            "item_format": "I",
            "divisor": 1000,
            "units": "mm",
            "number_format": "####.#",
        }
        self.ramped_standard_item_info = {
            "item_name": self.standard_item_name,
            "item_format": "I",
            "divisor": 1000,
            "units": "mm",
            "number_format": "#.###",
        }
        self.check_item_info = {
            "item_name": self.check_item_name,
            "item_format": "I",
            "divisor": 1000,
            "units": "mm",
            "number_format": "#.#",
        }
        self.check_data_source_info = {
            "ts_type": "CheckSeries",
            "data_type": "Rain6",
            "interpolation": "Discrete",
            "item_format": "140",
        }
        self.ramped_check_data_source_info = {
            "ts_type": "CheckSeries",
            "data_type": "SimpleTimeSeries",
            "interpolation": "Discrete",
            "item_format": "140",
        }
        self.standard_data_source_info = {
            "ts_type": "StdSeries",
            "data_type": "Rain6",
            "interpolation": "Incremental",
            "item_format": "0",
        }
        self.ramped_standard_data_source_info = {
            "ts_type": "StdSeries",
            "data_type": "SimpleTimeSeries",
            "interpolation": "Incremental",
            "item_format": "0",
        }
        self.ramped_standard = None
        self.ltco = None

    def import_data(
        self,
        from_date: str | None = None,
        to_date: str | None = None,
        standard: bool = True,
        check: bool = True,
        quality: bool = True,
    ):
        """
        Import data using the class parameter range.

        Overrides Processor.import_data to specify that the standard data is irregular and
        that a periodic frequency should not be inferred.


        Parameters
        ----------
        from_date : str, optional
            Start of data to import, will attempt to find last automation date if not set
        to_date : str, optional
            End of data to import, will default to current time if not set
        standard : bool, optional
            Whether to import standard data, by default True.
        check : bool, optional
            Whether to import check data, by default True.
        quality : bool, optional
            Whether to import quality data, by default False.

        Returns
        -------
        None

        Notes
        -----
        This method imports data for the specified date range, using the class
        parameters `_from_date` and `_to_date`. It updates the internal series data in
        the Processor instance for standard, check, and quality measurements
        separately.

        Examples
        --------
        >>> processor = RFProcessor(base_url="https://hilltop-server.com", site="Site1")
        >>> processor.import_data("2022-01-01", "2022-12-31",standard=True, check=True)
        False
        """
        if standard:
            (
                self._standard_data,
                self.raw_standard_data,
                self.raw_standard_xml,
                self.raw_standard_blob,
            ) = self.import_standard(
                standard_hts_filename=self.standard_hts_filename,
                site=self.site,
                standard_measurement_name=self._standard_measurement_name,
                standard_data_source_name=self.standard_data_source_name,
                standard_item_info=self.standard_item_info,
                standard_data=self._standard_data,
                from_date=from_date,
                to_date=to_date,
            )
        if quality:
            (
                self._quality_data,
                self.raw_quality_data,
                self.raw_standard_xml,
                self.raw_standard_blob,
            ) = self.import_quality(
                standard_hts_filename=self.standard_hts_filename,
                site=self._site,
                standard_measurement_name=self._standard_measurement_name,
                standard_data_source_name=self.standard_data_source_name,
                quality_data=self.quality_data,
                from_date=from_date,
                to_date=to_date,
            )
        if check:
            (
                self._check_data,
                self.raw_check_data,
                self.raw_standard_xml,
                self.raw_standard_blob,
            ) = self.import_check(
                check_hts_filename=self.check_hts_filename,
                site=self._site,
                check_measurement_name=self._check_measurement_name,
                check_data_source_name=self.check_data_source_name,
                check_item_info=self.check_item_info,
                check_item_name=self.check_item_name,
                check_data=self.check_data,
                from_date=from_date,
                to_date=to_date,
            )

    @ClassLogger
    def import_check(
        self,
        check_hts_filename: str | None = None,
        site: str | None = None,
        check_measurement_name: str | None = None,
        check_data_source_name: str | None = None,
        check_item_info: dict | None = None,
        check_item_name: str | None = None,
        check_data: pd.DataFrame | None = None,
        from_date: str | None = None,
        to_date: str | None = None,
        base_url: str | None = None,
    ):
        """
        Replacement for generic import check data.

        Parameters
        ----------
        check_hts_filename : str or None, optional
            Where to get check data from
        site : str or None, optional
            Which site to get data from
        check_measurement_name : str or None, optional
            Name for measurement to get
        check_data_source_name : str or None, optional
            Name for data source to get
        check_item_info : dict or None, optional
            ItemInfo to be used in hilltop xml
        check_item_name : str or None, optional
            ItemName to be used in hilltop xml
        check_data : pd.DataFrame or None, optional
            data which just gets overwritten I think? should maybe be removed
        from_date : str or None, optional
            The start date for data retrieval. If None, defaults to the earliest available
            data.
        to_date : str or None, optional
            The end date for data retrieval. If None, defaults to latest available
            data.
        base_url : str, optional
            Base of the url to use for the hilltop server request. Defaults to the Processor value.

        Returns
        -------
        check_data: pd.DataFrame
        raw_check_data: pd.DataFrame
        raw_check_xml: xml.etree.ElementTree
        raw_check_blob: DataSourceBlob

        Raises
        ------
        TypeError
            If the parsed Check data is not a pandas.DataFrame.

        Warnings
        --------
        UserWarning
            - If the existing Check Data is not a pandas.DataFrame, it is set to an
                empty DataFrame.
            - If no Check data is available for the specified date range.
            - If the Check data source is not found in the server response.

        Notes
        -----
        This method imports Check data from the specified server based on the provided
        parameters. It retrieves data using the `data_acquisition.get_data` function.
        The data is parsed and formatted according to the item_info in the data source.

        """
        (
            check_data,
            raw_check_data,
            raw_check_xml,
            raw_check_blob,
        ) = super().import_check(
            check_hts_filename,
            site,
            check_measurement_name,
            check_data_source_name,
            check_item_info,
            check_item_name,
            check_data,
            from_date,
            to_date,
            base_url,
        )
        check_data = utils.series_rounder(check_data)
        return check_data, raw_check_data, raw_check_xml, raw_check_blob

    @ClassLogger
    def quality_encoder(
        self,
        gap_limit: int | None = None,
        max_qc: int | float | None = None,
        supplemental_data: pd.Series | None = None,
        manual_additional_points: pd.Series | None = None,
        synthetic_checks: list | None = None,
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
        manual_additional_points : pd.Series or None, optional
            Used for capping the qc of given time points
            e.g. if dipstick is used or snow is present
            If None no points are added
        synthetic_checks : list | None
            list of datetimes (will have pd.Timestamp applied, so can have str)
             to have synthetic checks to replace recorded checks

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
        if manual_additional_points is None:
            manual_additional_points = pd.Series({})
        else:
            manual_additional_points = utils.series_rounder(manual_additional_points)

        if synthetic_checks:
            self.replace_checks_with_ltco(synthetic_checks)
        # Select all check data values that are marked to be used for QC purposes
        checks_for_qcing = self.check_data[self.check_data["QC"]]

        # If no check data, set to empty series
        checks_for_qcing = (
            checks_for_qcing["Value"] if "Value" in checks_for_qcing else pd.Series({})
        )

        # List of synthetic checks to find
        list_of_replaced_checks = [pd.Timestamp(time) for time in synthetic_checks]
        list_of_replaced_checks.sort()
        checks_to_300 = utils.series_rounder(
            pd.Series(index=pd.DatetimeIndex(list_of_replaced_checks), data=np.nan)
        )
        prior_checks_to_300 = pd.Series(
            data=checks_for_qcing.index, index=checks_for_qcing.index
        ).shift(1)[checks_to_300.index]
        prior_checks_to_300 = pd.Series(index=prior_checks_to_300, data=300)

        # Round all checks to the nearest 6min
        checks_for_qcing = utils.series_rounder(checks_for_qcing)

        start_date = pd.to_datetime(self.from_date)

        # If the start date is not a date stamp in the standard data set, insert a zero
        if start_date not in self.standard_data.index:
            self.standard_data = pd.concat(
                [
                    pd.DataFrame(
                        [[0.0, 0, "SRT", "Starting date added for ramping"]],
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

        site_survey_frame = rf.rainfall_nems_site_matrix(self.site)

        if self.from_date not in site_survey_frame.index:
            site_survey_frame = (
                site_survey_frame.reindex(
                    site_survey_frame.index.append(
                        pd.DatetimeIndex([self.from_date])
                    ).sort_values()
                )
                .ffill()
                .bfill()
            )
        self.report_processing_issue(
            message_type="info", comment=str(site_survey_frame["output_dict"].iloc[-1])
        )
        site_survey_frame = site_survey_frame[site_survey_frame.index >= self.from_date]

        quality_series = rf.points_to_qc(
            [deviation_points, time_points, manual_additional_points], site_survey_frame
        )
        quality_series = quality_series.reindex(self.check_data.index, method="ffill")
        # filter to apply codes only to dates in start-end-range
        if self.from_date not in quality_series.index:
            quality_series[self.from_date] = np.nan
            quality_series = quality_series.sort_index().ffill()
            quality_series = quality_series[quality_series.index >= self.from_date]

        self.ramped_standard = ramped_standard
        qc_frame = quality_series.to_frame(name="Value")
        qc_frame["Code"] = "RFL"
        qc_frame["Details"] = "Rainfall custom quality encoding"
        self._apply_quality(qc_frame, replace=True)

        checks_to_300 = self.quality_data.reindex(checks_to_300.index, method="ffill")
        self._apply_quality(checks_to_300, replace=False)

        self.quality_data.loc[prior_checks_to_300.index] = np.nan
        prior_checks_to_300 = prior_checks_to_300.to_frame(name="Value")
        prior_checks_to_300["Code"] = "SYN"
        prior_checks_to_300["Details"] = "LTCO rainfall synthetic data"
        self._apply_quality(prior_checks_to_300, replace=False)

        if supplemental_data is not None:
            msg_frame = evaluator.missing_data_quality_code(
                supplemental_data,
                self.quality_data,
                gap_limit=gap_limit,
            )
            self._apply_quality(msg_frame)
        else:
            self.report_processing_issue(
                start_time=None,
                end_time=None,
                code="MSP",
                comment="MISSING SUPPLEMENTAL PARAMETER: Rainfall needs a supplemental"
                " data source to detect missing data.",
                series_type="quality",
                message_type="warning",
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

    def filter_manual_tips(self, check_query: pd.DataFrame, buffer_minutes: int = None):
        """
        Attempts to remove manual tips from standard_series.

        Parameters
        ----------
        check_query : pd.DataFrame
            The DataFrame of all the checks that have been done
        buffer_minutes : int, optional
            Amount of time to increase search radius for manual tips by

        Returns
        -------
        None, self.standard_data modified
        """
        for _, check in check_query.iterrows():
            if buffer_minutes is None:
                self.standard_data["Value"], issue = rf.manual_tip_filter(
                    self.standard_data["Value"],
                    check["start_time"],
                    check["end_time"],
                    check["primary_manual_tips"],
                    check["weather"],
                )
            else:
                self.standard_data["Value"], issue = rf.manual_tip_filter(
                    self.standard_data["Value"],
                    check["start_time"],
                    check["end_time"],
                    check["primary_manual_tips"],
                    check["weather"],
                    buffer_minutes=buffer_minutes,
                )
            if issue is not None:
                self.report_processing_issue(**issue)

    def plot_processing_overview_chart(self, fig=None, **kwargs):
        """
        Plot a processing overview chart for the rainfall data.

        Overrides Processor.plot_processing_overview_chart to include the ramped
        standard data.

        Parameters
        ----------
        fig : plt.Figure or None, optional
            The figure to plot on, by default None.
            If None, a new figure is created.
        kwargs : dict
            Additional keyword arguments to pass to the plot.

        Returns
        -------
        fig : plt.Figure
            The plotly figure with the plot.
        """
        tag_list = ["HTP", "INS", "SOE"]
        check_names = ["Check data", "Inspections", "SOE checks"]

        zeroed_cumulative_check_data = self.cumulative_check_data.copy()
        if not zeroed_cumulative_check_data.empty:
            zeroed_cumulative_check_data["Value"] = zeroed_cumulative_check_data[
                "Value"
            ].fillna(0)

            zeroed_cumulative_check_data["Value"] = (
                zeroed_cumulative_check_data["Value"]
                - zeroed_cumulative_check_data["Value"].iloc[0]
            )

        fig = plotter.plot_processing_overview_chart(
            self.cumulative_standard_data,
            self.quality_data,
            zeroed_cumulative_check_data,
            self.quality_code_evaluator.constant_check_shift,
            self.quality_code_evaluator.qc_500_limit,
            self.quality_code_evaluator.qc_600_limit,
            tag_list=tag_list,
            check_names=check_names,
            fig=fig,
            rain_control=True,
            **kwargs,
        )

        fig.add_trace(
            go.Scatter(
                x=self.ramped_standard.index,
                y=self.ramped_standard.to_numpy().cumsum(),
                mode="lines",
                name="Ramped Standard",
                line=dict(color="grey", dash="dash"),
            )
        )
        return fig

    def to_xml_data_structure(self, standard=True, quality=True, check=True):
        """
        Convert Processor object data to a list of XML data structures.

        Returns
        -------
        list of data_structure.DataSourceBlob
            List of DataSourceBlob instances representing the data in the Processor
            object.

        Notes
        -----
        This method converts the data in the Processor object, including standard,
        check, and quality series, into a list of DataSourceBlob instances. Each
        DataSourceBlob contains information about the site, data source, and associated
        data.

        Examples
        --------
        >>> processor = Processor(base_url="https://hilltop-server.com", site="Site1")
        >>> processor.import_data()
        >>> xml_data_list = processor.to_xml_data_structure()
        >>> # Convert Processor data to a list of XML data structures.
        """
        data_blob_list = []

        # If standard data is present, add it to the list of data blobs
        if standard:
            # scada
            data_blob_list += [
                data_structure.standard_to_xml_structure(
                    standard_item_info=self.standard_item_info,
                    standard_data_source_name=self.standard_data_source_name,
                    standard_data_source_info=self.standard_data_source_info,
                    standard_series=self.standard_data["Value"] * 1000,
                    site=self.site,
                    gap_limit=self._defaults.get("gap_limit"),
                )
            ]
            # ramped
            ramped_standard = filters.trim_series(
                self.ramped_standard, self.check_data["Value"]
            )
            ramped_standard = ramped_standard.copy() * 1000

            data_blob_list += [
                data_structure.standard_to_xml_structure(
                    standard_item_info=self.ramped_standard_item_info,
                    standard_data_source_name="Rainfall",
                    standard_data_source_info=self.ramped_standard_data_source_info,
                    standard_series=ramped_standard,
                    site=self.site,
                    gap_limit=self._defaults.get("gap_limit"),
                )
            ]

        # If check data is present, add it to the list of data blobs
        if check:
            recorder_time_item_info = {
                "item_name": "Recorder Time",
                "item_format": "D",
                "divisor": "1",
                "units": "",
                "number_format": "###",
            }
            recorder_total_item_info = {
                "item_name": "Recorder Total",
                "item_format": "I",
                "divisor": "1",
                "units": "",
                "number_format": "###",
            }
            comment_item_info = {
                "item_name": "Comment",
                "item_format": "S",
                "divisor": "1",
                "units": "",
                "number_format": "###",
            }

            # scada
            scaled_check_data = self.check_data.copy()
            scaled_check_data["Value"] = scaled_check_data["Value"] * 1000

            data_blob_list += [
                data_structure.check_to_xml_structure(
                    item_info_dicts=[
                        self.check_item_info,
                        recorder_time_item_info,
                        recorder_total_item_info,
                        comment_item_info,
                    ],
                    check_data_source_name="SCADA Rainfall",
                    check_data_source_info=self.check_data_source_info,
                    check_item_info=self.check_item_info,
                    check_data=scaled_check_data,
                    site=self.site,
                    check_data_selector=[
                        "Value",
                        "Recorder Time",
                        "Recorder Total",
                        "Comment",
                    ],
                )
            ]

            # ramped
            data_blob_list += [
                data_structure.check_to_xml_structure(
                    item_info_dicts=[
                        self.check_item_info,
                        recorder_time_item_info,
                        recorder_total_item_info,
                        comment_item_info,
                    ],
                    check_data_source_name="Rainfall",
                    check_data_source_info=self.ramped_check_data_source_info,
                    check_item_info=self.check_item_info,
                    check_data=scaled_check_data,
                    site=self.site,
                    check_data_selector=[
                        "Value",
                        "Recorder Time",
                        "Recorder Total",
                        "Comment",
                    ],
                )
            ]

        # If quality data is present, add it to the list of data blobs
        if quality:
            # scada
            data_blob_list += [
                data_structure.quality_to_xml_structure(
                    data_source_name=self.standard_data_source_name,
                    quality_series=self.quality_data["Value"],
                    site=self.site,
                )
            ]
            # ramped
            data_blob_list += [
                data_structure.quality_to_xml_structure(
                    data_source_name="Rainfall",
                    quality_series=self.quality_data["Value"],
                    site=self.site,
                )
            ]
        return data_blob_list

    def calculate_long_term_common_offset(self, threshold: int = 500):
        """
        Calculate long term common offset (ltco).

        Parameters
        ----------
        threshold : int
            Quality required to consider the value in the common offset

        Returns
        -------
        None
            Sets self.ltco to the long term common offset
        """
        historic_standard, _, _, _ = self.import_standard(
            standard_hts_filename=self.archive_standard_hts_filename,
            from_date="1800-01-01 00:00",
            to_date=datetime.now().strftime("%Y-%m-%d %H:%M"),
            base_url=self.archive_base_url,
            standard_data=processor.EMPTY_STANDARD_DATA.copy(),
        )
        historic_check, _, _, _ = self.import_check(
            check_hts_filename=self.archive_check_hts_filename,
            from_date="1800-01-01 00:00",
            to_date=datetime.now().strftime("%Y-%m-%d %H:%M"),
            base_url=self.archive_base_url,
            check_data=processor.EMPTY_CHECK_DATA.copy(),
        )
        historic_quality, _, _, _ = self.import_quality(
            standard_hts_filename=self.archive_standard_hts_filename,
            from_date="1800-01-01 00:00",
            to_date=datetime.now().strftime("%Y-%m-%d %H:%M"),
            base_url=self.archive_base_url,
            quality_data=processor.EMPTY_QUALITY_DATA.copy(),
        )
        self.ltco = rf.calculate_common_offset(
            historic_standard["Value"],
            historic_check["Value"] * 1000,
            historic_quality["Value"][historic_quality["Value"] > 0],
            threshold,
        )
        self.report_processing_issue(
            start_time=historic_standard.index[0],
            end_time=historic_standard.index[-1],
            code="LCO",
            comment=f"Long term common offset calculated to be: {self.ltco}",
            series_type="check",
            message_type="info",
        )

    def replace_checks_with_ltco(self, list_of_replaced_checks: [str]):
        """
        For each check in the list, replace the check with synthetic ltco check.

        Parameters
        ----------
        list_of_replaced_checks : [str]

        Returns
        -------
        None
        """
        if list_of_replaced_checks:
            if self.ltco is None:
                self.calculate_long_term_common_offset()
            list_of_replaced_checks = [
                pd.Timestamp(time) for time in list_of_replaced_checks
            ]
            list_of_replaced_checks.sort()

            checks_to_replace = utils.series_rounder(
                pd.Series(index=list_of_replaced_checks)
            )

            # How much rainfall has occurred according to scada
            incremental_series = utils.rainfall_six_minute_repacker(
                self.standard_data["Value"]
            ).cumsum()
            try:
                recorded_totals = incremental_series[
                    self.check_data["Value"].index
                ].diff()
            except KeyError as e:
                raise KeyError(
                    "Check data times not found in the standard series"
                ) from e

            for check in checks_to_replace.index:
                if check not in recorded_totals.index:
                    raise KeyError(f"No check to replace at {check}")
                else:
                    self.check_data.loc[check, "Value"] = (
                        recorded_totals.loc[check] * self.ltco
                    )

    def enforce_measurement_at_site(self, measurement_name, hilltop):
        """Raise exception if check data is not in check_hts.

        This function does not function properly for rainfall.

        Hilltoppy does not recognise rain6 data type.
        """
        pass
