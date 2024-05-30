"""Triad class."""

import re
import warnings

import numpy as np
import pandas as pd
import utils
from annalist.decorators import ClassLogger
from hilltoppy import Hilltop

from hydrobot import data_acquisition

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


class Triad:
    """A container for Time series data - up to standard, check, quality."""

    def __init__(
        self,
        base_url,
        site,
        from_date,
        to_date,
        frequency,
        std_measurement_name=None,
        std_hts=None,
        check_hts=None,
        check_measurement_name=None,
        quality_hts=None,
        quality_measurement_name=None,
        **kwargs,
    ):
        """Constructs the triad."""
        self.base_url = base_url
        self.site = site
        self.from_date = from_date
        self.to_date = to_date
        self.frequency = frequency

        self.std_measurement_name = std_measurement_name
        self.std_hts = std_hts

        if self.std_measurement_name is not None and self.std_hts is not None:
            self.std_hilltop = Hilltop(base_url, std_hts, **kwargs)
            if site not in self.std_hilltop.available_sites:
                raise ValueError(
                    f"{self.std_measurement_name} site '{self.site}' not found for both base_url and hts combos."
                    f"Available sites in {self.std_hts} are: "
                    f"{[s for s in self.std_hilltop.available_sites]}"
                )

            available_std_measurements = self.std_hilltop.get_measurement_list(site)
            matches = re.search(r"([^\[\n]+)(\[(.+)\])?", std_measurement_name)
            if matches is not None:
                self.std_item_name = matches.groups()[0].strip(" ")
                self.std_data_source_name = matches.groups()[2]
                if self.std_data_source_name is None:
                    self.std_data_source_name = self.std_item_name
            if std_measurement_name not in list(
                available_std_measurements.MeasurementName
            ):
                raise ValueError(
                    f"'{std_measurement_name}' not found at"
                    f" site '{site}'. "
                    "Available measurements are "
                    f"{list(available_std_measurements.MeasurementName)}"
                )
            self.standard_item_info = {
                "ItemName": self.std_item_name,
                "ItemFormat": "F",
                "Divisor": 1,
                "Units": "",
                "Format": "###.##",
            }
            self.standard_data = EMPTY_STANDARD_DATA.copy()
            self.standard_data, _, _, _ = self.import_standard(
                standard_hts=self.std_hts,
                site=self.site,
                standard_measurement_name=self.std_measurement_name,
                standard_data_source_name=self.std_data_source_name,
                standard_item_info=self.standard_item_info,
                standard_data=self.standard_data,
                from_date=self.from_date,
                to_date=self.to_date,
                frequency=self.frequency,
            )

        self.check_hts = check_hts
        self.check_measurement_name = check_measurement_name
        if self.check_hts is not None and self.check_measurement_name is not None:
            self.check_hilltop = Hilltop(base_url, check_hts, **kwargs)

            if site not in self.check_hilltop.available_sites:
                raise ValueError(
                    f"{self.check_measurement_name} site '{self.check_hts}' not found for both base_url and hts combos."
                    f"Available sites in {self.check_hts} are: "
                    f"{[s for s in self.check_hilltop.available_sites]}"
                )

            available_check_measurements = self.check_hilltop.get_measurement_list(
                self.site
            )

            matches = re.search(r"([^\[\n]+)(\[(.+)\])?", self.check_measurement_name)

            if matches is not None:
                self.check_item_name = matches.groups()[0].strip(" ")
                self.check_data_source_name = matches.groups()[2]
                if self.check_data_source_name is None:
                    self.check_data_source_name = self.check_item_name
            if check_measurement_name not in list(
                available_check_measurements.MeasurementName
            ):
                raise ValueError(
                    f"'{check_measurement_name}' not found at"
                    f" site '{site}'. "
                    "Available measurements are "
                    f"{list(available_check_measurements.MeasurementName)}"
                )

            self.check_item_info = {
                "ItemName": self.check_item_name,
                "ItemFormat": "F",
                "Divisor": 1,
                "Units": "",
                "Format": "$$$",
            }
            self.check_data = EMPTY_CHECK_DATA.copy()

            self.check_data = self.import_check(
                check_hts=self.check_hts,
                site=self.site,
                check_measurement_name=self.check_measurement_name,
                check_data_source_name=self.check_data_source_name,
                check_item_info=self.check_item_info,
                check_item_name=self.check_item_name,
                check_data=self.check_data,
                from_date=from_date,
                to_date=to_date,
            )

        self.quality_hts = quality_hts
        self.quality_measurement_name = quality_measurement_name
        if self.quality_hts is not None and self.quality_measurement_name is not None:
            self.quality_hilltop = Hilltop(base_url, quality_hts, **kwargs)

            if site not in self.quality_hilltop.available_sites:
                raise ValueError(
                    f"{self.quality_measurement_name} site '{self.quality_hts}' not found for both base_url and hts combos."
                    f"Available sites in {self.quality_hts} are: "
                    f"{[s for s in self.quality_hilltop.available_sites]}"
                )

            available_quality_measurements = self.quality_hilltop.get_measurement_list(
                self.site
            )

            matches = re.search(r"([^\[\n]+)(\[(.+)\])?", self.quality_measurement_name)

            if matches is not None:
                self.quality_item_name = matches.groups()[0].strip(" ")
                self.quality_data_source_name = matches.groups()[2]
                if self.quality_data_source_name is None:
                    self.quality_data_source_name = self.quality_item_name
            if quality_measurement_name not in list(
                available_quality_measurements.MeasurementName
            ):
                raise ValueError(
                    f"'{quality_measurement_name}' not found at"
                    f" site '{site}'. "
                    "Available measurements are "
                    f"{list(available_quality_measurements.MeasurementName)}"
                )

            self.quality_item_info = {
                "ItemName": self.quality_item_name,
                "ItemFormat": "F",
                "Divisor": 1,
                "Units": "",
                "Format": "###.##",
            }

            self.quality_data = EMPTY_QUALITY_DATA.copy()

            self.quality_data, _, _, _ = self.import_quality(
                standard_hts=self.quality_hts,
                site=self.site,
                standard_measurement_name=self.quality_measurement_name,
                standard_data_source_name=self.quality_data_source_name,
                quality_data=self.quality_data,
                from_date=self.from_date,
                to_date=self.to_date,
            )

    @ClassLogger
    def import_standard(
        self,
        standard_hts: str | None = None,
        site: str | None = None,
        standard_measurement_name: str | None = None,
        standard_data_source_name: str | None = None,
        standard_item_info: dict | None = None,
        standard_data: pd.DataFrame | None = None,
        from_date: str | None = None,
        to_date: str | None = None,
        frequency: str | None = None,
    ):
        """
        Import standard data.

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
        ValueError
            - If no standard data is found within the specified date range.


        TypeError
            If the parsed Standard data is not a pandas.Series.

        Warnings
        --------
        UserWarning
            - If the existing Standard Series is not a pandas.Series, it is set to an
            empty Series.

        Notes
        -----
        This method imports Standard data from the specified server based on the
        provided parameters.
        It retrieves data using the `data_acquisition.get_data` function and updates
        the Standard Series in the instance.
        The data is parsed and formatted according to the item_info in the data source.

        """
        if standard_hts is None:
            standard_hts = self.std_hts
        if site is None:
            site = self.site
        if standard_measurement_name is None:
            standard_measurement_name = self.std_measurement_name
        if standard_data_source_name is None:
            standard_data_source_name = self.std_data_source_name
        if standard_item_info is None:
            standard_item_info = self.standard_item_info
        if from_date is None:
            from_date = self.from_date
        if to_date is None:
            to_date = self.to_date
        if frequency is None:
            frequency = self.frequency

        if standard_data is None:
            standard_data = self.standard_data

        xml_tree, blob_list = data_acquisition.get_data(
            self.base_url,
            standard_hts,
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
            warnings.warn(
                "No standard data found within specified date range.",
                stacklevel=1,
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
                        standard_item_info["ItemName"] = blob.data_source.item_info[
                            0
                        ].std_item_name
                        standard_item_info["ItemFormat"] = blob.data_source.item_info[
                            0
                        ].item_format
                        standard_item_info["Divisor"] = blob.data_source.item_info[
                            0
                        ].divisor
                        standard_item_info["Units"] = blob.data_source.item_info[
                            0
                        ].units
                        standard_item_info["Format"] = blob.data_source.item_info[
                            0
                        ].format
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
                raw_standard_data = raw_standard_data.asfreq(
                    frequency, fill_value=np.NaN
                )
            if raw_standard_blob is not None:
                fmt = standard_item_info["ItemFormat"]
                div = standard_item_info["Divisor"]
            else:
                warnings.warn(
                    "Could not extract standard data format from data source. "
                    "Defaulting to float format.",
                    stacklevel=1,
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
        standard_hts: str | None = None,
        site: str | None = None,
        standard_measurement_name: str | None = None,
        standard_data_source_name: str | None = None,
        quality_data: pd.DataFrame | None = None,
        from_date: str | None = None,
        to_date: str | None = None,
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

        Warnings
        --------
        UserWarning
            - If the existing Quality Series is not a pandas.Series, it is set to an
                empty Series.
            - If no Quality data is available for the specified date range.
            - If Quality data is not found in the server response.

        Notes
        -----
        This method imports Quality data from the specified server based on the
        provided parameters. It retrieves data using the `data_acquisition.get_data`
        function and updates the Quality Series in the instance. The data is parsed and
        formatted according to the item_info in the data source.
        """
        if standard_hts is None:
            standard_hts = self.std_hts
        if site is None:
            site = self.site
        if standard_measurement_name is None:
            standard_measurement_name = self.std_measurement_name
        if standard_data_source_name is None:
            standard_data_source_name = self.std_data_source_name
        if from_date is None:
            from_date = self.from_date
        if to_date is None:
            to_date = self.to_date

        if quality_data is None:
            quality_data = self.quality_data

        xml_tree, blob_list = data_acquisition.get_data(
            self.base_url,
            standard_hts,
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
            warnings.warn(
                "No Quality data available for the range specified.",
                stacklevel=1,
            )
        else:
            date_format = "Calendar"
            for blob in blob_list:
                if (blob.data_source.name == standard_data_source_name) and (
                    blob.data_source.ts_type == "StdQualSeries"
                ):
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
                warnings.warn(
                    "No Quality data found in the server response.",
                    stacklevel=2,
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
        check_hts: str | None = None,
        site: str | None = None,
        check_measurement_name: str | None = None,
        check_data_source_name: str | None = None,
        check_item_info: dict | None = None,
        check_item_name: str | None = None,
        check_data: pd.DataFrame | None = None,
        from_date: str | None = None,
        to_date: str | None = None,
    ):
        """
        Import Check data.

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
        if check_hts is None:
            check_hts = self.check_hts
        if site is None:
            site = self.site
        if check_measurement_name is None:
            check_measurement_name = self.check_measurement_name
        if check_data_source_name is None:
            check_data_source_name = self.check_data_source_name
        if check_item_info is None:
            check_item_info = self.check_item_info
        if check_item_name is None:
            check_item_name = self.check_item_name
        if check_data is None:
            check_data = self.check_data
        if from_date is None:
            from_date = self.from_date
        if to_date is None:
            to_date = self.to_date

        xml_tree, blob_list = data_acquisition.get_data(
            self.base_url,
            check_hts,
            site,
            check_measurement_name,
            from_date,
            to_date,
            tstype="Check",
        )
        import_data = EMPTY_QUALITY_DATA.copy()
        raw_check_data = EMPTY_CHECK_DATA.copy()
        raw_check_blob = None
        raw_check_xml = None
        blob_found = False
        date_format = "Calendar"
        if blob_list is None or len(blob_list) == 0:
            warnings.warn(
                "No Check data available for the range specified.",
                stacklevel=2,
            )
        else:
            data_source_options = []
            for blob in blob_list:
                data_source_options += [blob.data_source.name]
                if (blob.data_source.name == check_data_source_name) and (
                    blob.data_source.ts_type == "CheckSeries"
                ):
                    # Found it. Now we extract it.
                    blob_found = True

                    date_format = blob.data.date_format

                    # This could be a pd.Series
                    import_data = blob.data.timeseries
                    if import_data is not None:
                        raw_check_blob = blob
                        raw_check_xml = xml_tree
                        raw_check_data = import_data
                        check_item_info["ItemName"] = blob.data_source.item_info[
                            0
                        ].std_item_name
                        check_item_info["ItemFormat"] = blob.data_source.item_info[
                            0
                        ].item_format
                        check_item_info["Divisor"] = blob.data_source.item_info[
                            0
                        ].divisor
                        check_item_info["Units"] = blob.data_source.item_info[0].units
                        check_item_info["Format"] = blob.data_source.item_info[0].format
            if not blob_found:
                warnings.warn(
                    f"Check data {check_data_source_name} not found in server "
                    f"response. Available options are {data_source_options}",
                    stacklevel=2,
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
