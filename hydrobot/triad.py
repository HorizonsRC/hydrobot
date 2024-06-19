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


class TriadStandard:
    """A container for Time series standard data."""

    def __init__(
        self,
        base_url,
        site,
        from_date,
        to_date,
        frequency,
        measurement_name=None,
        hts=None,
        **kwargs,
    ):
        """Constructs the standard triad."""
        self.base_url = base_url
        self.site = site
        self.from_date = from_date
        self.to_date = to_date
        self.frequency = frequency

        self.measurement_name = measurement_name
        self.hts = hts

        if self.measurement_name is not None and self.hts is not None:
            self.hilltop = Hilltop(base_url, hts, **kwargs)
            if site not in self.hilltop.available_sites:
                raise ValueError(
                    f"{self.measurement_name} site '{self.site}' not found for both base_url and hts combos."
                    f"Available sites in {self.hts} are: "
                    f"{[s for s in self.hilltop.available_sites]}"
                )

            available_measurements = self.hilltop.get_measurement_list(site)
            matches = re.search(r"([^\[\n]+)(\[(.+)\])?", measurement_name)
            if matches is not None:
                self.item_name = matches.groups()[0].strip(" ")
                self.data_source_name = matches.groups()[2]
                if self.data_source_name is None:
                    self.data_source_name = self.item_name
            if measurement_name not in list(available_measurements.MeasurementName):
                raise ValueError(
                    f"'{measurement_name}' not found at"
                    f" site '{site}'. "
                    "Available measurements are "
                    f"{list(available_measurements.MeasurementName)}"
                )

            self.item_info = {
                "ItemName": self.item_name,
                "ItemFormat": "F",
                "Divisor": 1,
                "Units": "",
                "Format": "###.##",
            }
            self.data = EMPTY_STANDARD_DATA.copy()

            self.data, _, _, _ = self.import_standard(
                hts=self.hts,
                site=self.site,
                measurement_name=self.measurement_name,
                data_source_name=self.data_source_name,
                item_info=self.item_info,
                data=self.data,
                from_date=self.from_date,
                to_date=self.to_date,
                frequency=self.frequency,
            )

    @ClassLogger
    def import_standard(
        self,
        hts: str | None = None,
        site: str | None = None,
        measurement_name: str | None = None,
        data_source_name: str | None = None,
        item_info: dict | None = None,
        data: pd.DataFrame | None = None,
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
        if hts is None:
            hts = self.hts
        if site is None:
            site = self.site
        if measurement_name is None:
            measurement_name = self.measurement_name
        if data_source_name is None:
            data_source_name = self.data_source_name
        if item_info is None:
            item_info = self.item_info
        if from_date is None:
            from_date = self.from_date
        if to_date is None:
            to_date = self.to_date
        if frequency is None:
            frequency = self.frequency

        if data is None:
            data = self.data

        xml_tree, blob_list = data_acquisition.get_data(
            self.base_url,
            hts,
            site,
            measurement_name,
            from_date,
            to_date,
            tstype="Standard",
        )

        blob_found = False

        date_format = "Calendar"
        data_source_list = []
        raw_data = EMPTY_STANDARD_DATA.copy()

        raw_blob = None
        raw_xml = None
        if blob_list is None or len(blob_list) == 0:
            warnings.warn(
                "No standard data found within specified date range.",
                stacklevel=1,
            )
        else:
            for blob in blob_list:
                data_source_list += [blob.data_source.name]
                if (blob.data_source.name == data_source_name) and (
                    blob.data_source.ts_type == "StdSeries"
                ):
                    raw_data = blob.data.timeseries
                    date_format = blob.data.date_format
                    if raw_data is not None:
                        # Found it. Now we extract it.
                        blob_found = True
                        raw_blob = blob
                        raw_xml = xml_tree
                        item_info["ItemName"] = blob.data_source.item_info[0].item_name
                        item_info["ItemFormat"] = blob.data_source.item_info[
                            0
                        ].item_format
                        item_info["Divisor"] = blob.data_source.item_info[0].divisor
                        item_info["Units"] = blob.data_source.item_info[0].units
                        item_info["Format"] = blob.data_source.item_info[0].format
            if not blob_found:
                raise ValueError(
                    f"Standard Data Not Found under name "
                    f"{measurement_name}. "
                    f"Available data sources are: {data_source_list}"
                )

            if not isinstance(raw_data, pd.DataFrame):
                raise TypeError(
                    "Expecting pd.DataFrame for Standard data, "
                    f"but got {type(raw_data)} from parser."
                )
            if not raw_data.empty:
                if date_format == "mowsecs":
                    raw_data.index = utils.mowsecs_to_datetime_index(raw_data.index)
                else:
                    raw_data.index = pd.to_datetime(raw_data.index)
                if frequency is not None:
                    raw_data = raw_data.asfreq(frequency, fill_value=np.NaN)
            if raw_blob is not None:
                fmt = item_info["ItemFormat"]
                div = item_info["Divisor"]
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
                raw_data.iloc[:, 0] = raw_data.iloc[:, 0].astype(int) / int(div)
            elif fmt == "F":
                raw_data.iloc[:, 0] = raw_data.iloc[:, 0].astype(np.float32) / float(
                    div
                )
            elif fmt == "D":  # Not sure if this would ever really happen, but...
                raw_data.iloc[:, 0] = utils.mowsecs_to_datetime_index(
                    raw_data.iloc[:, 0]
                )
            else:
                raise ValueError(f"Unknown Format Spec: {fmt}")

            data["Raw"] = raw_data.iloc[:, 0]
            data["Value"] = data["Raw"]

        return (
            data,
            raw_data,
            raw_xml,
            raw_blob,
        )


class TriadCheck:
    """A container for Time series check data."""

    def __init__(
        self,
        base_url,
        site,
        from_date,
        to_date,
        frequency,
        hts=None,
        measurement_name=None,
        **kwargs,
    ):
        """Constructs the triad."""
        self.base_url = base_url
        self.site = site
        self.from_date = from_date
        self.to_date = to_date
        self.frequency = frequency

        self.measurement_name = measurement_name
        self.hts = hts

        if self.measurement_name is not None and self.hts is not None:
            self.hilltop = Hilltop(base_url, hts, **kwargs)
            if site not in self.hilltop.available_sites:
                raise ValueError(
                    f"{self.measurement_name} site '{self.hts}' not found for both base_url and hts combos."
                    f"Available sites in {self.hts} are: "
                    f"{[s for s in self.hilltop.available_sites]}"
                )

            available_measurements = self.hilltop.get_measurement_list(self.site)
            matches = re.search(r"([^\[\n]+)(\[(.+)\])?", self.measurement_name)
            if matches is not None:
                self.item_name = matches.groups()[0].strip(" ")
                self.data_source_name = matches.groups()[2]
                if self.data_source_name is None:
                    self.data_source_name = self.item_name
            if measurement_name not in list(available_measurements.MeasurementName):
                raise ValueError(
                    f"'{measurement_name}' not found at"
                    f" site '{site}'. "
                    "Available measurements are "
                    f"{list(available_measurements.MeasurementName)}"
                )

            self.item_info = {
                "ItemName": self.item_name,
                "ItemFormat": "F",
                "Divisor": 1,
                "Units": "",
                "Format": "$$$",
            }
            self.data = EMPTY_CHECK_DATA.copy()

            self.data, _, _, _ = self.import_check(
                hts=self.hts,
                site=self.site,
                measurement_name=self.measurement_name,
                data_source_name=self.data_source_name,
                item_info=self.item_info,
                item_name=self.item_name,
                data=self.data,
                from_date=from_date,
                to_date=to_date,
            )

    @ClassLogger
    def import_check(
        self,
        hts: str | None = None,
        site: str | None = None,
        measurement_name: str | None = None,
        data_source_name: str | None = None,
        item_info: dict | None = None,
        item_name: str | None = None,
        data: pd.DataFrame | None = None,
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
        if hts is None:
            hts = self.hts
        if site is None:
            site = self.site
        if measurement_name is None:
            measurement_name = self.measurement_name
        if data_source_name is None:
            data_source_name = self.data_source_name
        if item_info is None:
            item_info = self.item_info
        if item_name is None:
            item_name = self.item_name
        if data is None:
            data = self.data
        if from_date is None:
            from_date = self.from_date
        if to_date is None:
            to_date = self.to_date

        xml_tree, blob_list = data_acquisition.get_data(
            self.base_url,
            hts,
            site,
            measurement_name,
            from_date,
            to_date,
            tstype="Check",
        )
        raw_data = EMPTY_CHECK_DATA.copy()
        raw_blob = None
        raw_xml = None
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
                if (blob.data_source.name == data_source_name) and (
                    blob.data_source.ts_type == "CheckSeries"
                ):
                    # Found it. Now we extract it.
                    blob_found = True

                    date_format = blob.data.date_format

                    # This could be a pd.Series
                    import_data = blob.data.timeseries
                    if import_data is not None:
                        raw_blob = blob
                        raw_xml = xml_tree
                        raw_data = import_data
                        item_info["ItemName"] = blob.data_source.item_info[0].item_name
                        item_info["ItemFormat"] = blob.data_source.item_info[
                            0
                        ].item_format
                        item_info["Divisor"] = blob.data_source.item_info[0].divisor
                        item_info["Units"] = blob.data_source.item_info[0].units
                        item_info["Format"] = blob.data_source.item_info[0].format
            if not blob_found:
                warnings.warn(
                    f"Check data {data_source_name} not found in server "
                    f"response. Available options are {data_source_options}",
                    stacklevel=2,
                )

            if not isinstance(raw_data, pd.DataFrame):
                raise TypeError(
                    f"Expecting pd.DataFrame for Check data, but got {type(raw_data)}"
                    "from parser."
                )
            if not raw_data.empty:
                if date_format == "mowsecs":
                    raw_data.index = utils.mowsecs_to_datetime_index(raw_data.index)
                else:
                    raw_data.index = pd.to_datetime(raw_data.index)

            if not raw_data.empty and raw_blob is not None:
                # TODO: Maybe this should happen in the parser?
                for i, item in enumerate(raw_blob.data_source.item_info):
                    fmt = item.item_format
                    div = item.divisor
                    col = raw_data.iloc[:, i]
                    if fmt == "I":
                        raw_data.iloc[:, i] = col.astype(int) / int(div)
                    elif fmt == "F":
                        raw_data.iloc[:, i] = col.astype(np.float32) / float(div)
                    elif fmt == "D":
                        if raw_data.iloc[:, i].dtype != pd.Timestamp:
                            if date_format == "mowsecs":
                                raw_data.iloc[:, i] = utils.mowsecs_to_datetime_index(
                                    col
                                )
                            else:
                                raw_data.iloc[:, i] = col.astype(pd.Timestamp)
                    elif fmt == "S":
                        raw_data.iloc[:, i] = col.astype(str)

            if not raw_data.empty:
                data["Raw"] = raw_data[item_name]
                data["Value"] = data["Raw"]
                data["Recorder Time"] = raw_data["Recorder Time"]
                data["Comment"] = raw_data["Comment"]
                data["Source"] = "HTP"
                data["QC"] = True
        return data, raw_data, raw_xml, raw_blob


class TriadQuality:
    """A container for Time series quality data."""

    def __init__(
        self,
        base_url,
        site,
        from_date,
        to_date,
        hts=None,
        measurement_name=None,
        **kwargs,
    ):
        """Constructs the quality triad."""
        self.base_url = base_url
        self.site = site
        self.from_date = from_date
        self.to_date = to_date

        self.measurement_name = measurement_name
        self.hts = hts

        if self.measurement_name is not None and self.hts is not None:
            self.hilltop = Hilltop(base_url, hts, **kwargs)
            if site not in self.hilltop.available_sites:
                raise ValueError(
                    f"{self.measurement_name} site '{self.hts}' not found for both base_url and hts combos."
                    f"Available sites in {self.hts} are: "
                    f"{[s for s in self.hilltop.available_sites]}"
                )

            available_measurements = self.hilltop.get_measurement_list(self.site)
            matches = re.search(r"([^\[\n]+)(\[(.+)\])?", self.measurement_name)
            if matches is not None:
                self.item_name = matches.groups()[0].strip(" ")
                self.data_source_name = matches.groups()[2]
                if self.data_source_name is None:
                    self.quality_data_source_name = self.item_name
            if measurement_name not in list(available_measurements.MeasurementName):
                raise ValueError(
                    f"'{measurement_name}' not found at"
                    f" site '{site}'. "
                    "Available measurements are "
                    f"{list(available_measurements.MeasurementName)}"
                )

            self.item_info = {
                "ItemName": self.item_name,
                "ItemFormat": "F",
                "Divisor": 1,
                "Units": "",
                "Format": "###.##",
            }

            self.data = EMPTY_QUALITY_DATA.copy()

            self.data, _, _, _ = self.import_quality(
                hts=self.hts,
                site=self.site,
                measurement_name=self.measurement_name,
                data_source_name=self.data_source_name,
                data=self.data,
                from_date=self.from_date,
                to_date=self.to_date,
            )

    @ClassLogger
    def import_quality(
        self,
        hts: str | None = None,
        site: str | None = None,
        measurement_name: str | None = None,
        data_source_name: str | None = None,
        data: pd.DataFrame | None = None,
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
        if hts is None:
            hts = self.hts
        if site is None:
            site = self.site
        if measurement_name is None:
            measurement_name = self.measurement_name
        if data_source_name is None:
            data_source_name = self.data_source_name
        if from_date is None:
            from_date = self.from_date
        if to_date is None:
            to_date = self.to_date

        if data is None:
            data = self.data

        xml_tree, blob_list = data_acquisition.get_data(
            self.base_url,
            hts,
            site,
            measurement_name,
            from_date,
            to_date,
            tstype="Quality",
        )

        blob_found = False
        raw_data = EMPTY_QUALITY_DATA.copy()
        raw_blob = None
        raw_xml = None

        if blob_list is None or len(blob_list) == 0:
            warnings.warn(
                "No Quality data available for the range specified.",
                stacklevel=1,
            )
        else:
            date_format = "Calendar"
            for blob in blob_list:
                if (blob.data_source.name == data_source_name) and (
                    blob.data_source.ts_type == "StdQualSeries"
                ):
                    # Found it. Now we extract it.
                    blob_found = True

                    raw_data = blob.data.timeseries
                    date_format = blob.data.date_format
                    if raw_data is not None:
                        # Found it. Now we extract it.
                        blob_found = True
                        raw_blob = blob
                        raw_xml = xml_tree
            if not blob_found:
                warnings.warn(
                    "No Quality data found in the server response.",
                    stacklevel=2,
                )

            if not isinstance(raw_data, pd.DataFrame):
                raise TypeError(
                    f"Expecting pd.DataFrame for Quality data, but got "
                    f"{type(raw_data)} from parser."
                )
            if not raw_data.empty:
                if date_format == "mowsecs":
                    raw_data.index = utils.mowsecs_to_datetime_index(raw_data.index)
                else:
                    raw_data.index = pd.to_datetime(raw_data.index)
            raw_data.iloc[:, 0] = raw_data.iloc[:, 0].astype(int, errors="ignore")

            data["Raw"] = raw_data.iloc[:, 0]
            data["Value"] = data["Raw"]
        return (
            data,
            raw_data,
            raw_xml,
            raw_blob,
        )
