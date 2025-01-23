"""Processor class."""

import re
import warnings
from datetime import datetime

import numpy as np
import pandas as pd
from annalist.annalist import Annalist
from annalist.decorators import ClassLogger
from hilltoppy import Hilltop

import hydrobot
from hydrobot import (
    data_acquisition,
    data_sources,
    data_structure,
    evaluator,
    filters,
    plotter,
    utils,
)

annalizer = Annalist()

EMPTY_STANDARD_DATA = pd.DataFrame(
    columns=[
        "Time",
        "Raw",
        "Value",
        "Changes",
        "Remove",
    ]
).set_index("Time")
EMPTY_CHECK_DATA = pd.DataFrame(
    columns=[
        "Time",
        "Raw",
        "Value",
        "Changes",
        "Recorder Time",
        "Comment",
        "Source",
        "QC",
    ]
).set_index("Time")
EMPTY_QUALITY_DATA = pd.DataFrame(
    columns=[
        "Time",
        "Raw",
        "Value",
        "Code",
        "Details",
    ]
).set_index("Time")


class Processor:
    """
    Processor class for handling data processing.

    Attributes
    ----------
    _defaults : dict
        The default settings.
    _site : str
        The site to be processed.
    _standard_measurement_name : str
        The standard measurement to be processed.
    _check_measurement_name : str
        The measurement to be checked.
    _base_url : str
        The base URL of the Hilltop server.
    _standard_hts_filename : str
        The standard Hilltop service.
    _check_hts_filename : str
        The Hilltop service to be checked.
    _frequency : str
        The frequency of the data.
    _from_date : str
        The start date of the data.
    _to_date : str
        The end date of the data.
    _quality_code_evaluator : QualityCodeEvaluator
        The quality code evaluator.
    _interval_dict : dict
        Determines how data with old checks is downgraded.
    _standard_data : pd.Series
        The standard series data.
    _check_data : pd.Series
        The series containing check data.
    _quality_data : pd.Series
        The quality series data.
    raw_standard_blob : Blob
        The raw standard data blob.
    raw_standard_xml : str
        The raw standard data XML.
    raw_quality_blob : Blob
        The raw quality data blob.
    raw_quality_xml : str
        The raw quality data XML.
    raw_check_blob : Blob
        The raw check data blob.
    raw_check_xml : str
        The raw check data XML.
    standard_item_name : str
        The name of the standard item.
    standard_data_source_name : str
        The name of the standard data source.
    check_item_name : str
        The name of the check item.
    check_data_source_name : str
        The name of the check data source.
    export_file_name : str
        Where the data is exported to. Used as default when exporting without specified

    """

    @ClassLogger  # type:ignore
    def __init__(
        self,
        base_url: str,
        site: str,
        standard_hts_filename: str,
        standard_measurement_name: str,
        frequency: str | None,
        from_date: str | None = None,
        to_date: str | None = None,
        check_hts_filename: str | None = None,
        check_measurement_name: str | None = None,
        defaults: dict | None = None,
        interval_dict: dict | None = None,
        constant_check_shift: float = 0,
        fetch_quality: bool = False,
        export_file_name: str | None = None,
        archive_base_url: str | None = None,
        archive_standard_hts_filename: str | None = None,
        archive_check_hts_filename: str | None = None,
        provisional_wq_filename: str | None = None,
        archive_standard_measurement_name: str | None = None,
        **kwargs,
    ):
        """
        Constructs all the necessary attributes for the Processor object.

        Parameters
        ----------
        base_url : str
            The base URL of the Hilltop server.
        site : str
            The site to be processed.
        standard_hts_filename : str
            The standard Hilltop service.
        standard_measurement_name : str
            The standard measurement to be processed.
        frequency : str
            The frequency of the data.
        from_date : str, optional
            The start date of the data (default is None).
        to_date : str, optional
            The end date of the data (default is None).
        check_hts_filename : str, optional
            The Hilltop service to be checked (default is None).
        check_measurement_name : str, optional
            The measurement to be checked (default is None).
        defaults : dict, optional
            The default settings (default is None).
        interval_dict : dict, optional
            Determines how data with old checks is downgraded
        export_file_name : string, optional
            Where the data is exported to. Used as default when exporting without specified filename.
        provisional_wq_filename : str, optional
            Filename for provisional WQ data to be converted to check
        archive_standard_measurement_name : str, optional
            standard_measurement_name used in the archve file used to find last processed time and for final exported data
        kwargs : dict
            Additional keyword arguments.
        """
        # Processing issues reporting setup
        self.processing_issues = pd.DataFrame(
            {
                "start_time": [],
                "end_time": [],
                "code": [],
                "comment": [],
                "series_type": [],
                "message_type": [],
            }
        ).astype(str)
        self.report_processing_issue(
            comment=f"Hydrobot Version: {hydrobot.__version__}",
            message_type="info",
            start_time=datetime.now().strftime("%Y-%m-%d %H:%M"),
        )

        # replacements
        if check_measurement_name is None:
            check_measurement_name = standard_measurement_name
        if interval_dict is None:
            interval_dict = {}
        if archive_standard_measurement_name is None:
            archive_standard_measurement_name = standard_measurement_name
        if pd.isna(from_date):
            from_date = data_acquisition.find_last_time(
                archive_base_url,
                archive_standard_hts_filename,
                site,
                archive_standard_measurement_name,
            )
            self.report_processing_issue(
                comment=f"from_date inferred as: {str(from_date)}",
                message_type="info",
            )
        if pd.isna(to_date):
            to_date = pd.Timestamp.now().round("s")
            self.report_processing_issue(
                comment=f"to_date inferred as: {str(to_date)}",
                message_type="info",
            )

        # set input values
        self._base_url = base_url
        self._site = site
        self._standard_hts_filename = standard_hts_filename
        self._standard_measurement_name = standard_measurement_name
        self._frequency = frequency
        self._from_date = from_date
        self._to_date = to_date
        self._check_hts_filename = check_hts_filename
        self._check_measurement_name = check_measurement_name
        self._defaults = defaults
        self._interval_dict = interval_dict
        self.export_file_name = export_file_name
        self.archive_base_url = archive_base_url
        self.archive_standard_hts_filename = archive_standard_hts_filename
        self.archive_check_hts_filename = archive_check_hts_filename
        self.archive_standard_measurement_name = archive_standard_measurement_name
        self.provisional_wq_filename = provisional_wq_filename

        # Set other value initial values
        self._standard_data = EMPTY_STANDARD_DATA.copy()
        self._check_data = EMPTY_CHECK_DATA.copy()
        self._quality_data = EMPTY_QUALITY_DATA.copy()

        self.raw_standard_blob = None
        self.raw_standard_xml = None
        self.raw_quality_blob = None
        self.raw_quality_xml = None
        self.raw_check_blob = None
        self.raw_check_xml = None

        # standard hilltop
        standard_hilltop = Hilltop(base_url, standard_hts_filename)
        self.enforce_site_in_hts(standard_hilltop, self.site)
        self.enforce_measurement_at_site(standard_measurement_name, standard_hilltop)

        def measurement_datasource_splitter(measurement_name):
            matches = re.search(r"([^\[\n]+)(\[(.+)\])?", measurement_name)
            item_name = matches.groups()[0].strip(" ")
            data_source_name = matches.groups()[2]
            if data_source_name is None:
                data_source_name = item_name
            return item_name, data_source_name

        (
            self.standard_item_name,
            self.standard_data_source_name,
        ) = measurement_datasource_splitter(standard_measurement_name)

        (
            self.archive_standard_item_name,
            self.archive_standard_data_source_name,
        ) = measurement_datasource_splitter(archive_standard_measurement_name)

        # check hilltop
        if check_hts_filename is not None:
            check_hilltop = Hilltop(base_url, check_hts_filename)
            self.enforce_site_in_hts(check_hilltop, self.site)
            self.enforce_measurement_at_site(check_measurement_name, check_hilltop)

        (
            self.check_item_name,
            self.check_data_source_name,
        ) = measurement_datasource_splitter(check_measurement_name)

        self.standard_item_info = {
            "item_name": self.standard_item_name,
            "item_format": "F",
            "divisor": 1,
            "units": "",
            "number_format": "###.##",
        }
        self.archive_standard_item_info = {
            "item_name": self.archive_standard_item_name,
            "item_format": "F",
            "divisor": 1,
            "units": "",
            "number_format": "###.##",
        }
        self.check_item_info = {
            "item_name": self.check_item_name,
            "item_format": "F",
            "divisor": 1,
            "units": "",
            "number_format": "$$$",
        }
        self.standard_data_source_info = {
            "ts_type": "StdSeries",
            "data_type": "SimpleTimeSeries",
            "interpolation": "Instant",
            "item_format": "1",
        }
        self.check_data_source_info = {
            "ts_type": "CheckSeries",
            "data_type": "SimpleTimeSeries",
            "interpolation": "Discrete",
            "item_format": "45",
        }

        self._quality_code_evaluator = data_sources.get_qc_evaluator(
            standard_measurement_name
        )
        if constant_check_shift is not None:
            self._quality_code_evaluator.constant_check_shift = constant_check_shift

        # Load data for the first time
        get_check = self.check_hts_filename is not None
        self.import_data(
            from_date=self.from_date,
            to_date=self.to_date,
            check=get_check,
            quality=fetch_quality,
        )

    def enforce_measurement_at_site(self, measurement_name, hilltop):
        """Unimplemented test that measurement is in a given hilltop."""
        pass
        """
        available_measurements = hilltop.get_measurement_list(self.site)
        if measurement_name not in list(available_measurements.MeasurementName):
            raise ValueError(
                f"Measurement name '{measurement_name}' not found at"
                f" site '{self.site}'. "
                "Available measurements are "
                f"{list(available_measurements.MeasurementName)}"
            )
        """

    def enforce_site_in_hts(self, hts: Hilltop, site: str):
        """Raise exception if site not in Hilltop file."""
        if site not in hts.available_sites:
            raise ValueError(
                f"Site '{site}' not found in hilltop file."
                f"Available sites in {hts} are: "
                f"{[s for s in hts.available_sites]}"
            )

    @classmethod
    def from_processing_parameters_dict(
        cls, processing_parameters, fetch_quality=False
    ):
        """
        Initialises a Processor class given a config file.

        Parameters
        ----------
        processing_parameters : dict
            Dictionary of processing parameters
        fetch_quality : bool, optional
            Whether to fetch any existing quality data, default false

        Returns
        -------
        Processor, Annalist
        """
        ###################################################################################
        # Setting up logging with Annalist
        ###################################################################################

        ann = Annalist()
        ann.configure(
            logfile=processing_parameters.get("logfile", None),
            analyst_name=processing_parameters["analyst_name"],
            stream_format_str=processing_parameters["format"].get("stream", None),
            file_format_str=processing_parameters["format"].get("file", None),
        )

        ###################################################################################
        # Creating a Hydrobot Processor object which contains the data to be processed
        ###################################################################################
        return cls(**processing_parameters, fetch_quality=fetch_quality), ann

    @classmethod
    def from_config_yaml(cls, config_path, fetch_quality=False, set_from_date=False):
        """
        Initialises a Processor class given a config file.

        Parameters
        ----------
        config_path : string
            Path to config.yaml.
        fetch_quality : bool, optional
            Whether to fetch any existing quality data, default false
        set_from_date : bool, optional
            If true, from_date in the config yaml is overwritten by the last date on the archive
            Requires "archive_base_url" and "archive_standard_hts_filename" in the yaml, in addition to "site" and
            "standard_measurement_name"

        Returns
        -------
        Processor, Annalist
        """
        processing_parameters = data_acquisition.config_yaml_import(config_path)

        if set_from_date:
            utils.set_config_from_date(
                config_file=config_path,
                base_url=processing_parameters["archive_base_url"],
                hts_filename=processing_parameters["archive_standard_hts_filename"],
                site=processing_parameters["site"],
                measurement=processing_parameters["standard_measurement_name"],
            )
            # refresh the parameters
            processing_parameters = data_acquisition.config_yaml_import(config_path)

        if "to_date" not in processing_parameters:
            processing_parameters["to_date"] = datetime.now().strftime(
                "%d-%m-%Y %H:%M:%S"
            )
        keys_to_be_set_to_none_if_missing = [
            "frequency",
            "from_date",
            "check_hts_filename",
            "check_measurement_name",
            "inspection_expiry",
            "export_file_name",
            "archive_base_url",
            "archive_standard_hts_filename",
            "archive_check_hts_filename",
        ]
        for k in keys_to_be_set_to_none_if_missing:
            if k not in processing_parameters:
                processing_parameters[k] = None

        def isvalid(potential_nan):
            return potential_nan is None or np.isnan(potential_nan)

        if (not isinstance(processing_parameters["frequency"], str)) and isvalid(
            processing_parameters["frequency"]
        ):
            processing_parameters["frequency"] = None

        return cls.from_processing_parameters_dict(processing_parameters, fetch_quality)

    @property
    def standard_measurement_name(self):  # type: ignore
        """str: The site to be processed."""
        return self._standard_measurement_name

    @property
    def site(self):  # type: ignore
        """str: The site to be processed."""
        return self._site

    @property
    def from_date(self):  # type: ignore
        """str: The start date of the data."""
        return self._from_date

    @property
    def to_date(self):  # type: ignore
        """str: The end date of the data."""
        return self._to_date

    @property
    def frequency(self):  # type: ignore
        """str: The frequency of the data."""
        return self._frequency

    @property
    def base_url(self):  # type: ignore
        """str: The base URL of the Hilltop server."""
        return self._base_url

    @property
    def standard_hts_filename(self):  # type: ignore
        """str: The standard Hilltop service."""
        return self._standard_hts_filename

    @property
    def check_hts_filename(self):  # type: ignore
        """str: The Hilltop service to be checked."""
        return self._check_hts_filename

    @property
    def quality_code_evaluator(self):  # type: ignore
        """Measurement property."""
        return self._quality_code_evaluator

    @ClassLogger
    @quality_code_evaluator.setter
    def quality_code_evaluator(self, value):
        self._quality_code_evaluator = value

    @property
    def defaults(self):  # type: ignore
        """dict: The default settings."""
        return self._defaults

    @property  # type: ignore
    def standard_data(self) -> pd.DataFrame:  # type: ignore
        """pd.Series: The standard series data."""
        return self._standard_data

    @ClassLogger  # type: ignore
    @standard_data.setter
    def standard_data(self, value):
        self._standard_data = value

    @property  # type: ignore
    def check_data(self) -> pd.DataFrame:  # type: ignore
        """pd.Series: The series containing check data."""
        return self._check_data

    @ClassLogger  # type: ignore
    @check_data.setter
    def check_data(self, value):
        self._check_data = value

    @property  # type: ignore
    def quality_data(self) -> pd.DataFrame:  # type: ignore
        """pd.Series: The quality series data."""
        return self._quality_data

    @ClassLogger  # type: ignore
    @quality_data.setter
    def quality_data(self, value):
        self._quality_data = value

    @ClassLogger
    def import_standard(
        self,
        standard_hts_filename: str | None = None,
        site: str | None = None,
        standard_measurement_name: str | None = None,
        standard_data_source_name: str | None = None,
        standard_item_info: dict | None = None,
        standard_data: pd.DataFrame | None = None,
        from_date: str | None = None,
        to_date: str | None = None,
        frequency: str | None = None,
        infer_frequency: bool = True,
        base_url: str | None = None,
    ):
        """
        Import standard data.

        Parameters
        ----------
        standard_hts_filename : str or None, optional
            The standard Hilltop service. If None, defaults to the standard HTS.
        site : str or None, optional
            The site to be processed. If None, defaults to the site on the processor object.
        standard_measurement_name : str or None, optional
            The standard measurement to be processed. If None, defaults to the standard
            measurement name on the processor object.
        standard_data_source_name : str or None, optional
            The name of the standard data source. If None, defaults to the standard data
            source name on the processor object.
        standard_item_info : dict or None, optional
            The item information for the standard data. If None, defaults to the
            standard item info on the processor object.
        standard_data : pd.DataFrame or None, optional
            The standard data. If None, defaults to the standard data on the processor
            object.
        from_date : str or None, optional
            The start date for data retrieval. If None, defaults to the earliest available
            data.
        to_date : str or None, optional
            The end date for data retrieval. If None, defaults to latest available
            data.
        frequency : str or None, optional
            The frequency of the data. If None, defaults to the frequency on the
            processor object. If that's also None, the infer_frequency is consulted to
            determine whether to infer the frequency from the data.
        infer_frequency : bool, optional
            Whether to infer the frequency from the data. If True, the frequency is
            inferred from the data. If False, the frequency is set to None. Only used if
            the frequency is not provided as a parameter AND not specified on the
            processor object.
        base_url : str or None, optional
            URL to look for hilltop server. Will use self.base_url if None.

        Returns
        -------
        None

        Raises
        ------
        ValueError
            - If no standard data is found within the specified date range.


        TypeError
            If the parsed Standard data is not a pandas.Series.

        Notes
        -----
        This method imports Standard data from the specified server based on the
        provided parameters.
        It retrieves data using the `data_acquisition.get_data` function and updates
        the Standard Series in the instance.
        The data is parsed and formatted according to the item_info in the data source.

        Examples
        --------
        >>> processor = Processor(...)  # initialize processor instance
        >>> processor.import_standard(
        ...     from_date='2022-01-01', to_date='2022-01-10'
        ... )
        """
        if standard_hts_filename is None:
            standard_hts_filename = self._standard_hts_filename
        if site is None:
            site = self._site
        if standard_measurement_name is None:
            standard_measurement_name = self._standard_measurement_name
        if standard_data_source_name is None:
            standard_data_source_name = self.standard_data_source_name
        if standard_item_info is None:
            standard_item_info = self.standard_item_info
        if from_date is None:
            from_date = self.from_date
        if to_date is None:
            to_date = self.to_date
        if frequency is None:
            frequency = self._frequency
        if standard_data is None:
            standard_data = self._standard_data
        if base_url is None:
            base_url = self._base_url

        xml_tree, blob_list = data_acquisition.get_data(
            base_url,
            standard_hts_filename,
            site,
            standard_measurement_name,
            from_date,
            to_date,
            tstype="Standard",
        )

        blob_found = False

        date_format = "Calendar"
        data_source_list = []
        raw_standard_data = EMPTY_STANDARD_DATA.copy()

        raw_standard_blob = None
        raw_standard_xml = None
        if blob_list is None or len(blob_list) == 0:
            self.report_processing_issue(
                start_time=from_date,
                end_time=to_date,
                series_type="Standard",
                message_type="error",
                comment="No standard data found within specified date range.",
                code="MSD",
            )
        else:
            for blob in blob_list:
                data_source_list += [blob.data_source.name]
                if (blob.data_source.name == standard_data_source_name) and (
                    blob.data_source.ts_type == "StdSeries"
                ):
                    raw_standard_data = blob.data.timeseries

                    date_format = blob.data.date_format
                    if raw_standard_data is not None:
                        # Found it. Now we extract it.
                        blob_found = True
                        raw_standard_blob = blob
                        raw_standard_xml = xml_tree
                        standard_item_info["item_name"] = blob.data_source.item_info[
                            0
                        ].item_name
                        standard_item_info["item_format"] = blob.data_source.item_info[
                            0
                        ].item_format
                        standard_item_info["divisor"] = blob.data_source.item_info[
                            0
                        ].divisor
                        standard_item_info["units"] = blob.data_source.item_info[
                            0
                        ].units
                        standard_item_info[
                            "number_format"
                        ] = blob.data_source.item_info[0].number_format
            if not blob_found:
                raise ValueError(
                    f"Standard Data Not Found under name "
                    f"{standard_measurement_name}. "
                    f"Available data sources are: {data_source_list}"
                )

            if not isinstance(raw_standard_data, pd.DataFrame):
                raise TypeError(
                    "Expecting pd.DataFrame for Standard data, "
                    f"but got {type(raw_standard_data)} from parser."
                )

            if not raw_standard_data.empty:
                if date_format == "mowsecs":
                    raw_standard_data.index = utils.mowsecs_to_datetime_index(
                        raw_standard_data.index
                    )
                else:
                    raw_standard_data.index = pd.to_datetime(raw_standard_data.index)

                if frequency is not None:
                    # Frequency is provided
                    raw_standard_data = raw_standard_data.asfreq(
                        frequency, fill_value=np.nan
                    )
                else:
                    if infer_frequency:
                        # We have been asked to infer the frequency
                        frequency = utils.infer_frequency(
                            raw_standard_data.index, method="mode"
                        )
                        raw_standard_data = raw_standard_data.asfreq(
                            frequency, fill_value=np.nan
                        )
                        self.report_processing_issue(
                            code="IRR",
                            comment=f"frequency inferred as {frequency}",
                            message_type="info",
                        )
                        self._frequency = frequency
                    else:
                        # infer_frequency is explicitly set to false and frequency is None
                        # Assuming irregular data
                        self.report_processing_issue(
                            code="IRR",
                            comment="No frequency provided and infer_frequency is set to False. "
                            "Assuming irregular data.",
                            message_type="warning",
                        )

            if self.raw_standard_blob is not None:
                fmt = standard_item_info["item_format"]
                div = standard_item_info["divisor"]
            else:
                self.report_processing_issue(
                    code="HXD",
                    comment="Could not extract standard data format from data source. "
                    "Defaulting to float format.",
                    series_type="standard",
                    message_type="error",
                )

                fmt = "F"
                div = 1
            if div is None or div == "None":
                div = 1
            if fmt == "I":
                raw_standard_data.iloc[:, 0] = raw_standard_data.iloc[:, 0].astype(
                    int
                ) / int(div)
            elif fmt == "F":
                raw_standard_data.iloc[:, 0] = raw_standard_data.iloc[:, 0].astype(
                    np.float32
                ) / float(div)
            elif fmt == "D":  # Not sure if this would ever really happen, but...
                raw_standard_data.iloc[:, 0] = utils.mowsecs_to_datetime_index(
                    raw_standard_data.iloc[:, 0]
                )
            else:
                raise ValueError(f"Unknown Format Spec: {fmt}")

            standard_data["Raw"] = raw_standard_data.iloc[:, 0]
            standard_data["Value"] = standard_data["Raw"]

        return (
            standard_data,
            raw_standard_data,
            raw_standard_xml,
            raw_standard_blob,
        )

    @ClassLogger
    def import_quality(
        self,
        standard_hts_filename: str | None = None,
        site: str | None = None,
        standard_measurement_name: str | None = None,
        standard_data_source_name: str | None = None,
        quality_data: pd.DataFrame | None = None,
        from_date: str | None = None,
        to_date: str | None = None,
        base_url: str | None = None,
    ):
        """
        Import quality data.

        Parameters
        ----------
        from_date : str or None, optional
            The start date for data retrieval. If None, defaults to the earliest available
            data.
        to_date : str or None, optional
            The end date for data retrieval. If None, defaults to latest available
            data.

        Returns
        -------
        None

        Raises
        ------
        TypeError
            If the parsed Quality data is not a pandas.Series.

        Notes
        -----
        This method imports Quality data from the specified server based on the
        provided parameters. It retrieves data using the `data_acquisition.get_data`
        function and updates the Quality Series in the instance. The data is parsed and
        formatted according to the item_info in the data source.

        Examples
        --------
        >>> processor = Processor(...)  # initialize processor instance
        >>> processor.import_quality(
        ...     from_date='2022-01-01', to_date='2022-01-10', overwrite=True
        ... )
        """
        if standard_hts_filename is None:
            standard_hts_filename = self._standard_hts_filename
        if site is None:
            site = self.site
        if standard_measurement_name is None:
            standard_measurement_name = self._standard_measurement_name
        if standard_data_source_name is None:
            standard_data_source_name = self.standard_data_source_name
        if from_date is None:
            from_date = self.from_date
        if to_date is None:
            to_date = self.to_date
        if quality_data is None:
            quality_data = self._quality_data
        if base_url is None:
            base_url = self._base_url

        xml_tree, blob_list = data_acquisition.get_data(
            base_url,
            standard_hts_filename,
            site,
            standard_measurement_name,
            from_date,
            to_date,
            tstype="Quality",
        )

        blob_found = False
        raw_quality_data = EMPTY_QUALITY_DATA.copy()
        raw_quality_blob = None
        raw_quality_xml = None

        if blob_list is None or len(blob_list) == 0:
            self.report_processing_issue(
                start_time=from_date,
                end_time=to_date,
                series_type="Quality",
                message_type="error",
                comment="No quality data found within specified date range, len0",
                code="MQD",
            )
        else:
            date_format = "Calendar"
            for blob in blob_list:
                data_source_options = []
                if blob.data_source.ts_type == "StdQualSeries":
                    data_source_options += [blob.data_source.name]
                    if blob.data_source.name == standard_data_source_name:
                        # Found it. Now we extract it.
                        blob_found = True

                        raw_quality_data = blob.data.timeseries
                        date_format = blob.data.date_format
                        if raw_quality_data is not None:
                            # Found it. Now we extract it.
                            blob_found = True
                            raw_quality_blob = blob
                            raw_quality_xml = xml_tree
            if not blob_found:
                self.report_processing_issue(
                    start_time=from_date,
                    end_time=to_date,
                    series_type="Quality",
                    message_type="error",
                    comment="No quality data found within specified date range "
                    "and with correct standard data source name"
                    f"Quality data {standard_data_source_name} not found in server "
                    f"response. Available options are {data_source_options}",
                    code="MQD",
                )

            if not isinstance(raw_quality_data, pd.DataFrame):
                raise TypeError(
                    f"Expecting pd.DataFrame for Quality data, but got "
                    f"{type(raw_quality_data)} from parser."
                )
            if not raw_quality_data.empty:
                if date_format == "mowsecs":
                    raw_quality_data.index = utils.mowsecs_to_datetime_index(
                        raw_quality_data.index
                    )
                else:
                    raw_quality_data.index = pd.to_datetime(raw_quality_data.index)
            raw_quality_data.iloc[:, 0] = raw_quality_data.iloc[:, 0].astype(
                int, errors="ignore"
            )

            quality_data["Raw"] = raw_quality_data.iloc[:, 0]
            quality_data["Value"] = quality_data["Raw"]
        return (
            quality_data,
            raw_quality_data,
            raw_quality_xml,
            raw_quality_blob,
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
        Import Check data.

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

        Notes
        -----
        This method imports Check data from the specified server based on the provided
        parameters. It retrieves data using the `data_acquisition.get_data` function.
        The data is parsed and formatted according to the item_info in the data source.

        Examples
        --------
        >>> processor = Processor(...)  # initialize processor instance
        >>> processor.import_check(
        ...     from_date='2022-01-01', to_date='2022-01-10', overwrite=True
        ... )
        """
        if check_hts_filename is None:
            check_hts_filename = self.check_hts_filename
        if site is None:
            site = self._site
        if check_measurement_name is None:
            check_measurement_name = self._check_measurement_name
        if check_data_source_name is None:
            check_data_source_name = self.check_data_source_name
        if check_item_info is None:
            check_item_info = self.check_item_info
        if check_item_name is None:
            check_item_name = self.check_item_name
        if check_data is None:
            check_data = self._check_data
        if from_date is None:
            from_date = self._from_date
        if to_date is None:
            to_date = self._to_date
        if base_url is None:
            base_url = self._base_url

        xml_tree, blob_list = data_acquisition.get_data(
            base_url,
            check_hts_filename,
            site,
            check_measurement_name,
            from_date,
            to_date,
            tstype="Check",
        )
        raw_check_data = EMPTY_CHECK_DATA.copy()
        raw_check_blob = None
        raw_check_xml = None
        blob_found = False
        date_format = "Calendar"
        if blob_list is None or len(blob_list) == 0:
            self.report_processing_issue(
                start_time=from_date,
                end_time=to_date,
                series_type="Check",
                message_type="error",
                comment="No check data found within specified date range.",
                code="MCD",
            )
        else:
            data_source_options = []
            for blob in blob_list:
                data_source_options += [blob.data_source.name]
                if (
                    blob.data_source.name
                    in [check_data_source_name, self.standard_data_source_name]
                ) and (blob.data_source.ts_type == "CheckSeries"):
                    # Found it. Now we extract it.
                    blob_found = True

                    date_format = blob.data.date_format

                    # This could be a pd.Series
                    import_data = blob.data.timeseries
                    if import_data is not None:
                        raw_check_blob = blob
                        raw_check_xml = xml_tree
                        raw_check_data = import_data
                        check_item_info["item_name"] = blob.data_source.item_info[
                            0
                        ].item_name
                        check_item_info["item_format"] = blob.data_source.item_info[
                            0
                        ].item_format
                        check_item_info["divisor"] = blob.data_source.item_info[
                            0
                        ].divisor
                        check_item_info["units"] = blob.data_source.item_info[0].units
                        check_item_info["number_format"] = blob.data_source.item_info[
                            0
                        ].number_format
            if not blob_found:
                self.report_processing_issue(
                    start_time=from_date,
                    end_time=to_date,
                    series_type="Check",
                    message_type="error",
                    comment=f"Check data {check_data_source_name} not found in server "
                    f"response. Available options are {data_source_options}",
                    code="MCD",
                )

            if not isinstance(raw_check_data, pd.DataFrame):
                raise TypeError(
                    f"Expecting pd.DataFrame for Check data, but got {type(raw_check_data)}"
                    "from parser."
                )
            if not raw_check_data.empty:
                if date_format == "mowsecs":
                    raw_check_data.index = utils.mowsecs_to_datetime_index(
                        raw_check_data.index
                    )
                else:
                    raw_check_data.index = pd.to_datetime(raw_check_data.index)

            if not raw_check_data.empty and raw_check_blob is not None:
                # TODO: Maybe this should happen in the parser?
                for i, item in enumerate(raw_check_blob.data_source.item_info):
                    fmt = item.item_format
                    div = item.divisor
                    col = raw_check_data.iloc[:, i]
                    if fmt == "I":
                        raw_check_data.iloc[:, i] = col.astype(int) / int(div)
                    elif fmt == "F":
                        raw_check_data.iloc[:, i] = col.astype(np.float32) / float(div)
                    elif fmt == "D":
                        if raw_check_data.iloc[:, i].dtype != pd.Timestamp:
                            if date_format == "mowsecs":
                                raw_check_data.iloc[
                                    :, i
                                ] = utils.mowsecs_to_datetime_index(col)
                            else:
                                raw_check_data.iloc[:, i] = col.astype(pd.Timestamp)
                    elif fmt == "S":
                        raw_check_data.iloc[:, i] = col.astype(str)

            if not raw_check_data.empty:
                check_data["Raw"] = raw_check_data[check_item_name]
                check_data["Value"] = check_data["Raw"]
                check_data["Recorder Time"] = raw_check_data["Recorder Time"]
                check_data["Comment"] = raw_check_data["Comment"]
                check_data["Source"] = "HTP"
                check_data["QC"] = True
        return check_data, raw_check_data, raw_check_xml, raw_check_blob

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

        Parameters
        ----------
        from_date : str or None, optional
            start of data to be imported, if None will use defaults
        to_date : str or None, optional
            end of data to be imported, if None will use defaults
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
        >>> processor = Processor(base_url="https://hilltop-server.com", site="Site1")
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
                frequency=self._frequency,
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
    def add_standard(self, extra_standard):
        """
        Incorporate extra standard data into the standard series using utils.merge_series.

        Parameters
        ----------
        extra_standard
            extra standard data

        Returns
        -------
        None, but adds data to self.standard_data
        """
        combined = utils.merge_series(self.standard_data["Value"], extra_standard)
        self.standard_data["Value"] = combined

    @ClassLogger
    def add_check(self, extra_check):
        """
        Incorporate extra check data into the check series using utils.merge_series.

        Parameters
        ----------
        extra_check
            extra check data

        Returns
        -------
        None, but adds data to self.check_series
        """
        combined = utils.merge_series(self.check_data["Value"], extra_check)
        self.check_data["Value"] = combined

    @ClassLogger
    def add_quality(self, extra_quality):
        """
        Incorporate extra quality data into the quality series using utils.merge_series.

        Parameters
        ----------
        extra_quality
            extra quality data

        Returns
        -------
        None, but adds data to self.quality_series
        """
        combined = utils.merge_series(self.quality_data["Value"], extra_quality)
        self.quality_data["Value"] = combined

    @ClassLogger
    def gap_closer(self, gap_limit: int | None = None):
        """
        Close small gaps in the standard series.

        DEPRECATED: The use of this method is discouraged as it completely removes rows
        from the dataframes. The gap closing functionality has been moved to
        data_exporter, where gaps are handled automatically before data export.

        Parameters
        ----------
        gap_limit : int or None, optional
            The maximum number of consecutive missing values to close, by default None.
            If None, the gap limit from the class defaults is used.

        Returns
        -------
        None

        Notes
        -----
        This method closes small gaps in the standard series by replacing consecutive
        missing values with interpolated or backfilled values. The gap closure is
        performed using the evaluator.small_gap_closer function.

        Examples
        --------
        >>> processor = Processor(base_url="https://hilltop-server.com", site="Site1")
        >>> processor.gap_closer(gap_limit=5)
        >>> processor.standard_data["Value"]
        <updated standard series with closed gaps>
        """
        warnings.warn(
            "DEPRECATED: The use of gap_closer is discouraged as it completely "
            "removes rows from the dataframes.",
            category=DeprecationWarning,
            stacklevel=1,
        )
        if gap_limit is None:
            if "gap_limit" not in self._defaults:
                raise ValueError("gap_limit value required, no value found in defaults")
            else:
                gap_limit = int(self._defaults["gap_limit"])

        gapless = evaluator.small_gap_closer(
            self._standard_data["Value"].squeeze(), gap_limit=gap_limit
        )
        self._standard_data = self._standard_data.loc[gapless.index]

    @ClassLogger
    def quality_encoder(
        self,
        gap_limit: int | None = None,
        max_qc: int | float | None = None,
        interval_dict: dict | None = None,
    ):
        """
        Encode quality information in the quality series.

        Parameters
        ----------
        gap_limit : int or None, optional
            The maximum number of consecutive missing values to consider as gaps, by
            default None.
            If None, the gap limit from the class defaults is used.
        max_qc : numeric or None, optional
            Maximum quality code possible at site
            If None, the max qc from the class defaults is used.
        interval_dict : dict or None, optional
            Dictionary that dictates when to downgrade data with old checks
            Takes pd.DateOffset:quality_code pairs
            If None, the interval_dict from the class defaults is used.

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
        if gap_limit is None:
            if "gap_limit" not in self._defaults:
                raise ValueError("gap_limit value required, no value found in defaults")
            else:
                gap_limit = int(self._defaults["gap_limit"])
        if max_qc is None:
            max_qc = self._defaults["max_qc"] if "max_qc" in self._defaults else np.nan

        if interval_dict is None:
            interval_dict = self._interval_dict

        qc_checks = self.check_data[self.check_data["QC"]]
        qc_series = qc_checks["Value"] if "Value" in qc_checks else pd.Series({})

        if self.check_data.empty:
            self.quality_data.loc[pd.Timestamp(self.from_date), "Value"] = 200
            self.quality_data.loc[pd.Timestamp(self.to_date), "Value"] = 0
            self.quality_data.loc[pd.Timestamp(self.from_date), "Code"] = "EMT"
            self.quality_data.loc[pd.Timestamp(self.to_date), "Code"] = "EMT, END"
            self.quality_data.loc[
                pd.Timestamp(self.from_date), "Details"
            ] = "Empty data, start time set to qc200"
            self.quality_data.loc[
                pd.Timestamp(self.to_date), "Details"
            ] = "Empty data, qc0 at end"
        else:
            chk_frame = evaluator.check_data_quality_code(
                self.standard_data["Value"],
                qc_series,
                self._quality_code_evaluator,
            )
            self._apply_quality(chk_frame, replace=True)

        oov_frame = evaluator.bulk_downgrade_out_of_validation(
            self.quality_data, qc_series, interval_dict
        )
        self._apply_quality(oov_frame)

        msg_frame = evaluator.missing_data_quality_code(
            self.standard_data["Value"],
            self.quality_data,
            gap_limit=gap_limit,
        )
        self._apply_quality(msg_frame)

        lim_frame = evaluator.max_qc_limiter(self.quality_data, max_qc)
        self._apply_quality(lim_frame)

    def _apply_quality(
        self,
        changed_data,
        replace=False,
    ):
        if replace:
            self.quality_data = changed_data
        else:
            # Step 1: Merge the dataframes using an outer join
            merged_df = self.quality_data.merge(
                changed_data,
                how="outer",
                left_index=True,
                right_index=True,
                suffixes=("_old", "_new"),
            )

            # Step 2: Replace NaN values in df1 with corresponding values from df2
            with pd.option_context("future.no_silent_downcasting", True):
                # This context + infer_objects protects against pandas deprecation + warning
                merged_df["Value"] = (
                    merged_df["Value_old"]
                    .fillna(merged_df["Value_new"])
                    .infer_objects(copy=False)
                )
                merged_df["Code"] = (
                    merged_df["Code_old"]
                    .fillna(merged_df["Code_new"])
                    .infer_objects(copy=False)
                )

                merged_df["Details"] = (
                    merged_df["Details_old"]
                    .fillna(merged_df["Details_new"])
                    .infer_objects(copy=False)
                )

            # Step 3: Combine the two dataframes, prioritizing non-null values from df2
            self.quality_data = merged_df[["Value", "Code", "Details"]].combine_first(
                self.quality_data
            )

    def clip(self, low_clip: float | None = None, high_clip: float | None = None):
        """
        Clip data within specified low and high values.

        Parameters
        ----------
        low_clip : float or None, optional
            The lower bound for clipping, by default None.
            If None, the low clip value from the class defaults is used.
        high_clip : float or None, optional
            The upper bound for clipping, by default None.
            If None, the high clip value from the class defaults is used.

        Returns
        -------
        None

        Notes
        -----
        This method clips the data in both the standard and check series within the
        specified low and high values. It uses the filters.clip function for the actual
        clipping process.

        Examples
        --------
        >>> processor = Processor(base_url="https://hilltop-server.com", site="Site1")
        >>> processor.clip(low_clip=0, high_clip=100)
        >>> processor.standard_data["Value"]
        <clipped standard series within the specified range>
        >>> processor.check_data["Value"]
        <clipped check series within the specified range>
        """
        if low_clip is None:
            low_clip = (
                float(self._defaults["low_clip"])
                if "low_clip" in self._defaults
                else np.nan
            )
        if high_clip is None:
            high_clip = (
                float(self._defaults["high_clip"])
                if "high_clip" in self._defaults
                else np.nan
            )

        clipped = filters.clip(
            self._standard_data["Value"].squeeze(), low_clip, high_clip
        )

        self._standard_data = self._apply_changes(
            self._standard_data, clipped, "CLP", mark_remove=True
        )

    @staticmethod
    def _apply_changes(
        dataframe,
        changed_values,
        change_code,
        mark_remove=False,
    ):
        both_none_mask = pd.isna(dataframe["Value"]) & pd.isna(changed_values)

        # Create a mask for cases where values are different excluding both being None-like
        diffs_mask = (dataframe["Value"] != changed_values) & ~both_none_mask

        if mark_remove:
            dataframe.loc[diffs_mask, "Remove"] = mark_remove
        dataframe.loc[diffs_mask, "Changes"] = change_code
        dataframe["Value"] = changed_values
        return dataframe

    @ClassLogger
    def remove_outliers(self, span: int | None = None, delta: float | None = None):
        """
        Remove outliers from the data.

        Parameters
        ----------
        span : int or None, optional
            The span parameter for smoothing, by default None.
            If None, the span value from the class defaults is used.
        delta : float or None, optional
            The delta parameter for identifying outliers, by default None.
            If None, the delta value from the class defaults is used.

        Returns
        -------
        None

        Notes
        -----
        This method removes outliers from the standard series using the specified
        span and delta values. It utilizes the filters.remove_outliers function for
        the actual outlier removal process.

        Examples
        --------
        >>> processor = Processor(base_url="https://hilltop-server.com", site="Site1")
        >>> processor.remove_outliers(span=10, delta=2.0)
        >>> processor.standard_data["Value"]
        <standard series with outliers removed>
        """
        if span is None:
            if "span" not in self._defaults:
                raise ValueError("span value required, no value found in defaults")
            else:
                span = int(self._defaults["span"])
        if delta is None:
            if "delta" not in self._defaults:
                raise ValueError("delta value required, no value found in defaults")
            else:
                delta = float(self._defaults["delta"])

        rm_outliers = filters.remove_outliers(
            self._standard_data["Value"].squeeze(), span, delta
        )

        self._standard_data = self._apply_changes(
            self._standard_data, rm_outliers, "OUT", mark_remove=True
        )

    @ClassLogger
    def remove_spikes(
        self,
        low_clip: float | None = None,
        high_clip: float | None = None,
        span: int | None = None,
        delta: float | None = None,
    ):
        """
        Remove spikes from the data.

        Parameters
        ----------
        low_clip : float or None, optional
            The lower clipping threshold, by default None.
            If None, the low_clip value from the class defaults is used.
        high_clip : float or None, optional
            The upper clipping threshold, by default None.
            If None, the high_clip value from the class defaults is used.
        span : int or None, optional
            The span parameter for smoothing, by default None.
            If None, the span value from the class defaults is used.
        delta : float or None, optional
            The delta parameter for identifying spikes, by default None.
            If None, the delta value from the class defaults is used.

        Returns
        -------
        None

        Notes
        -----
        This method removes spikes from the standard series using the specified
        parameters. It utilizes the filters.remove_spikes function for the actual
        spike removal process.

        Examples
        --------
        >>> processor = Processor(base_url="https://hilltop-server.com", site="Site1")
        >>> processor.remove_spikes(low_clip=10, high_clip=20, span=5, delta=2.0)
        >>> processor.standard_data["Value"]
        <standard series with spikes removed>
        """
        if low_clip is None:
            low_clip = (
                float(self._defaults["low_clip"])
                if "low_clip" in self._defaults
                else np.nan
            )
        if high_clip is None:
            high_clip = (
                float(self._defaults["high_clip"])
                if "low_clip" in self._defaults
                else np.nan
            )
        if span is None:
            if "span" not in self._defaults:
                raise ValueError("span value required, no value found in defaults")
            else:
                span = int(self._defaults["span"])
        if delta is None:
            if "delta" not in self._defaults:
                raise ValueError("delta value required, no value found in defaults")
            else:
                delta = float(self._defaults["delta"])

        rm_spikes = filters.remove_spikes(
            self._standard_data["Value"].squeeze(),
            span,
            low_clip,
            high_clip,
            delta,
        )

        self._standard_data = self._apply_changes(
            self._standard_data, rm_spikes, "SPK", mark_remove=True
        )

    @ClassLogger
    def remove_flatlined_values(self, span: int = 3):
        """Remove repeated values in std series a la flatline_value_remover()."""
        rm_fln = filters.flatline_value_remover(self._standard_data["Value"], span=span)

        self._standard_data = self._apply_changes(
            self._standard_data, rm_fln, "FLN", mark_remove=True
        )

    @ClassLogger
    def remove_range(
        self,
        from_date,
        to_date,
    ):
        """
        Mark a range in standard_data for removal.

        Parameters
        ----------
        from_date : str
            The start date of the range to delete.
        to_date : str
            The end date of the range to delete.


        Returns
        -------
        None

        Notes
        -----
        This method deletes a specified range of data from the selected time series
        types. The range is defined by the `from_date` and `to_date` parameters.

        Examples
        --------
        >>> processor = Processor(base_url="https://hilltop-server.com", site="Site1")
        >>> processor.remove_range(from_date="2022-01-01", to_date="2022-12-31", \
                tstype_standard=True)
        >>> processor.standard_data
        <standard series with specified range deleted>
        >>> processor.remove_range(from_date="2022-01-01", to_date="2022-12-31", \
                tstype_check=True)
        >>> processor.check_data
        <check series with specified range deleted>
        """
        rm_range = filters.remove_range(
            self._standard_data["Value"],
            from_date,
            to_date,
            insert_gaps="all",
        )
        self.standard_data = self._apply_changes(
            self._standard_data, rm_range, "MAN", mark_remove=True
        )

    @ClassLogger
    def delete_range(
        self,
        from_date,
        to_date,
        tstype_standard=True,
        tstype_check=False,
        tstype_quality=False,
        gap_limit=None,
    ):
        """
        Delete a range of data from specified time series types.

        DEPRECATED: The use of this method is discouraged as it completely removes rows
        from the dataframes. User is encouraged to use 'remove_range' which marks rows
        for removal, but retains the timestamp to be associated with the other values
        in the row such as the raw value, reason for removal, etc.

        Parameters
        ----------
        from_date : str
            The start date of the range to delete.
        to_date : str
            The end date of the range to delete.
        tstype_standard : bool, optional
            Flag to delete data from the standard series, by default True.
        tstype_check : bool, optional
            Flag to delete data from the check series, by default False.
        tstype_quality : bool, optional
            Flag to delete data from the quality series, by default False.
        gap_limit : int, optional
            How big missing data is required to insert a gap.

        Returns
        -------
        None

        Notes
        -----
        This method deletes a specified range of data from the selected time series
        types. The range is defined by the `from_date` and `to_date` parameters.

        Examples
        --------
        >>> processor = Processor(base_url="https://hilltop-server.com", site="Site1")
        >>> processor.delete_range(from_date="2022-01-01", to_date="2022-12-31", \
                tstype_standard=True)
        >>> processor.standard_data
        <standard series with specified range deleted>
        >>> processor.delete_range(from_date="2022-01-01", to_date="2022-12-31", \
                tstype_check=True)
        >>> processor.check_data
        <check series with specified range deleted>
        """
        warnings.warn(
            message="DEPRECATED: The use of delete_range is discouraged as it completely "
            "removes rows from the dataframes. User is encouraged to use "
            "'remove_range' which marks rows for removal, but retains the timestamp "
            "to be associated with the other values "
            "in the row such as the raw value, reason for removal, etc.",
            category=DeprecationWarning,
            stacklevel=1,
        )
        if gap_limit is None:
            if "gap_limit" in self._defaults:
                gap_limit = self._defaults["gap_limit"]
            else:
                raise ValueError("gap_limit value required, no value found in defaults")

        if tstype_standard:
            self.standard_data = filters.remove_range(
                self._standard_data,
                from_date,
                to_date,
                min_gap_length=gap_limit,
                insert_gaps="start",
            )
        if tstype_check:
            self.check_data = filters.remove_range(
                self._check_data,
                from_date,
                to_date,
                min_gap_length=gap_limit,
                insert_gaps="start",
            )
        if tstype_quality:
            self.quality_data = filters.remove_range(
                self._quality_data,
                from_date,
                to_date,
                min_gap_length=gap_limit,
                insert_gaps="start",
            )

    @ClassLogger
    def pad_data_with_nan_to_set_freq(self):
        """
        Set the data to the correct frequency, filled with NaNs as appropriate.

        Returns
        -------
        None

        Notes
        -----
        This method adjusts the time series data to the correct frequency,
        filling missing values with NaNs as appropriate. It modifies the
        standard series in-place.

        Examples
        --------
        >>> processor = Processor(base_url="https://hilltop-server.com", site="Site1")
        >>> processor.pad_data_with_nan_to_set_freq()
        >>> processor.standard_data
        <standard series with missing values filled with NaNs>
        """
        self.standard_data = self._standard_data.asfreq(self._frequency)

    @ClassLogger
    def data_exporter(
        self,
        file_location=None,
        ftype="xml",
        standard: bool = True,
        quality: bool = True,
        check: bool = True,
        trimmed=True,
    ):
        """
        Export data to file.

        Parameters
        ----------
        file_location : str | None
            The file path where the file will be saved. If 'ftype' is "csv" or "xml",
            this should be a full file path including extension. If 'ftype' is
            "hilltop_csv", multiple files will be created, so 'file_location' should be
            a prefix that will be appended with "_std_qc.csv" for the file containing
            the standard and quality data, and "_check.csv" for the check data file.
            If None, uses self.export_file_name
        ftype : str, optional
            Avalable options are "xml", "hilltop_csv", "csv", "check".
        standard : bool, optional
            Whether standard data is exported, default true
        check : bool, optional
            Whether check data is exported, default true
        quality : bool, optional
            Whether quality data is exported, default true
        trimmed : bool, optional
            If True, export trimmed data; otherwise, export the full data.
            Default is True.

        Returns
        -------
        None

        Raises
        ------
        ValueError
            - If ftype is not a recognised string

        Notes
        -----
        This method exports data to a CSV file.

        Examples
        --------
        >>> processor = Processor(base_url="https://hilltop-server.com", site="Site1")
        >>> processor.data_exporter("output.xml", trimmed=True)
        >>> # Check the generated XML file at 'output.xml'
        """
        if file_location is None:
            file_location = self.export_file_name
        export_selections = [standard, quality, check]
        if trimmed:
            std_data = filters.trim_series(
                self._standard_data["Value"],
                self._check_data["Value"],
            )
        else:
            std_data = self._standard_data

        if ftype == "csv":
            all_data = [
                self._standard_data["Value"],
                self._quality_data["Value"],
                self._check_data["Value"],
            ]
            columns = ["Standard", "Quality", "Check"]

            for data, col in zip(all_data, columns, strict=True):
                data.name = col

            export_list = [
                i for (i, v) in zip(all_data, export_selections, strict=True) if v
            ]
            data_sources.series_export_to_csv(file_location, series=export_list)
        elif ftype == "hilltop_csv":
            data_sources.hilltop_export(
                file_location,
                self._site,
                std_data,
                self._check_data["Value"],
                self._quality_data["Value"],
            )
        elif ftype == "xml":
            if self.check_data.empty:
                check = False
            blob_list = self.to_xml_data_structure(
                standard=standard, quality=quality, check=check
            )
            data_structure.write_hilltop_xml(blob_list, file_location)
        else:
            raise ValueError("Invalid ftype (filetype)")

    def diagnosis(self):
        """
        Provide a diagnosis of the data.

        Returns
        -------
        None

        Notes
        -----
        This method analyzes the state of the data, including the standard,
        check, and quality series. It provides diagnostic information about
        the data distribution, gaps, and other relevant characteristics.

        Examples
        --------
        >>> processor = Processor(base_url="https://hilltop-server.com", site="Site1")
        >>> processor.import_data()
        >>> processor.diagnosis()
        >>> # View diagnostic information about the data.
        """
        evaluator.diagnose_data(
            self._standard_data["Value"],
            self._check_data["Value"],
            self._quality_data["Value"],
            self._frequency,
        )

    def plot_raw_data(self, fig=None, **kwargs):
        """Implement plotting.plot_raw_data."""
        fig = plotter.plot_raw_data(self.standard_data["Raw"], fig=fig, **kwargs)

        return fig

    def plot_qc_codes(self, fig=None, **kwargs):
        """Implement plotting.plot_qc_codes."""
        fig = plotter.plot_qc_codes(
            self.standard_data["Value"],
            self.quality_data["Value"],
            fig=fig,
            **kwargs,
        )

        return fig

    def add_qc_limit_bars(self, fig=None, **kwargs):
        """Implement plotting.add_qc_limit_bars."""
        fig = plotter.add_qc_limit_bars(
            self.quality_code_evaluator.qc_500_limit,
            self.quality_code_evaluator.qc_600_limit,
            fig=fig,
            **kwargs,
        )

        return fig

    def plot_check_data(
        self,
        tag_list=None,
        check_names=None,
        ghosts=False,
        diffs=False,
        align_checks=False,
        fig=None,
        **kwargs,
    ):
        """Implement plotting.plot_qc_codes."""
        fig = plotter.plot_check_data(
            self.standard_data["Value"],
            self.quality_data,
            self.quality_code_evaluator.constant_check_shift,
            tag_list=tag_list,
            check_names=check_names,
            ghosts=ghosts,
            diffs=diffs,
            align_checks=align_checks,
            fig=fig,
            **kwargs,
        )

        return fig

    def plot_processing_overview_chart(self, fig=None, **kwargs):
        """
        Plot a processing overview chart.

        Parameters
        ----------
        fig :  plotly.graph_objects.Figure, optional
            The figure to plot on, by default None.
        kwargs : dict
            Additional keyword arguments to pass to the plot

        Returns
        -------
        plotly.graph_objects.Figure
            The figure with the processing overview chart.
        """
        tag_list = ["HTP", "INS", "SOE"]
        check_names = ["Check data", "Inspections", "SOE checks"]

        fig = plotter.plot_processing_overview_chart(
            self.standard_data,
            self.quality_data,
            self.check_data,
            self.quality_code_evaluator.constant_check_shift,
            self.quality_code_evaluator.qc_500_limit,
            self.quality_code_evaluator.qc_600_limit,
            tag_list=tag_list,
            check_names=check_names,
            fig=fig,
            **kwargs,
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
            data_blob_list += [
                data_structure.standard_to_xml_structure(
                    self.archive_standard_item_info,
                    self.archive_standard_data_source_name,
                    self.standard_data_source_info,
                    self.standard_data["Value"],
                    self.site,
                    self._defaults.get("gap_limit"),
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
            comment_item_info = {
                "item_name": "Comment",
                "item_format": "S",
                "divisor": "1",
                "units": "",
                "number_format": "###",
            }

            data_blob_list += [
                data_structure.check_to_xml_structure(
                    item_info_dicts=[
                        self.check_item_info,
                        recorder_time_item_info,
                        comment_item_info,
                    ],
                    check_data_source_name=self.check_data_source_name,
                    check_data_source_info=self.check_data_source_info,
                    check_item_info=self.check_item_info,
                    check_data=self.check_data,
                    site=self.site,
                    check_data_selector=["Value", "Recorder Time", "Comment"],
                )
            ]

        # If quality data is present, add it to the list of data blobs
        if quality:
            data_blob_list += [
                data_structure.quality_to_xml_structure(
                    data_source_name=self.archive_standard_data_source_name,
                    quality_series=self.quality_data["Value"],
                    site=self.site,
                )
            ]
        return data_blob_list

    def report_processing_issue(
        self,
        start_time=None,
        end_time=None,
        code=None,
        comment=None,
        series_type=None,
        message_type=None,
    ):
        """
        Add an issue to be reported for processing usage.

        This method adds an issue to the processing_issues DataFrame.

        Parameters
        ----------
        start_time : str | None
            The start time of the issue.
        end_time : str | None
            The end time of the issue.
        code : str | None
            The code of the issue.
        comment : str | None
            The comment of the issue.
        series_type : str | None
            The type of the series the issue is related to.
        message_type : str | None
            Should be one of: ["debug", "info", "warning", "error"]

        """
        self.processing_issues = pd.concat(
            [
                pd.DataFrame(
                    [
                        [
                            start_time,
                            end_time,
                            code,
                            comment,
                            series_type,
                            message_type,
                        ]
                    ],
                    columns=self.processing_issues.columns,
                    dtype=object,
                ),
                self.processing_issues,
            ],
            ignore_index=True,
        )

    def get_measurement_dataframe(self, measurement, hts_type):
        """Get a dataframe of a given measurement for other processor parameters."""
        if hts_type == "standard":
            hts = self._standard_hts_filename
        elif hts_type == "check":
            hts = self._check_hts_filename
        else:
            raise ValueError(f"Invalid hts_type {hts_type}")

        return data_acquisition.get_server_dataframe(
            self._base_url,
            hts,
            self.site,
            measurement,
            self.from_date,
            self.to_date,
        )
