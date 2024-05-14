"""DataSourceBlob Object."""
import re
import warnings
from xml.etree import ElementTree

import pandas as pd
from defusedxml import ElementTree as DefusedElementTree


class ItemInfo:
    """Item Info Class."""

    def __init__(
        self,
        item_number: int,
        item_name: str,
        item_format: str,
        divisor: str,
        units: str,
        format: str,
    ):
        """
        Initialize an ItemInfo instance.

        Parameters
        ----------
        item_number : int
            The item number associated with the item information.
        item_name : str
            The name of the item.
        item_format : str
            The format of the item.
        divisor : str
            The divisor associated with the item.
        units : str
            The units of measurement for the item.
        format : str
            The format of the item information.

        Returns
        -------
        None
        """
        self.item_number = item_number
        self.item_name = item_name
        self.item_format = item_format
        self.divisor = divisor
        self.units = units
        self.format = format

    @classmethod
    def from_xml(cls, source):
        """
        Create an ItemInfo instance from XML.

        Parameters
        ----------
        source : str or ElementTree.Element or bytes or bytearray or file-like object
            The XML source to parse and create an ItemInfo instance.

        Returns
        -------
        ItemInfo
            An instance of ItemInfo created from the XML source.

        Raises
        ------
        ValueError
            If the XML source type is not supported or if the XML structure is invalid.

        Notes
        -----
        This class method reads an object from XML, extracting information to create
        an ItemInfo instance.

        Examples
        --------
        >>> xml_string = "<ItemInfo ItemNumber='1'><ItemName>Example</ItemName></ItemInfo>"
        >>> item_info_instance = ItemInfo.from_xml(xml_string)
        >>> isinstance(item_info_instance, ItemInfo)
        True
        """
        if isinstance(source, str):
            # If the source is a string, treat it as raw XML
            root = DefusedElementTree.fromstring(source)
        elif isinstance(source, ElementTree.Element):
            # If the source is an ElementTree object, use it directly
            root = source
        elif isinstance(source, bytes | bytearray):
            # If the source is a bytes or bytearray, assume it's
            # XML content and decode it.
            root = DefusedElementTree.fromstring(source.decode())
        elif hasattr(source, "read"):
            # If the source has a 'read' method, treat it as a
            # file-like object.
            root = DefusedElementTree.parse(source).getroot()
        else:
            raise ValueError("Unsupported XML source type.")

        if root.tag == "ItemInfo":
            item_number = int(root.attrib["ItemNumber"])
        else:
            raise ValueError(
                "Tag at ItemInfo level should be 'ItemInfo'," f" found {root.tag}."
            )

        item_name = str(root.findtext("ItemName"))
        item_format = str(root.findtext("ItemFormat"))
        divisor = str(root.findtext("Divisor"))
        units = str(root.findtext("Units"))
        format = str(root.findtext("Format"))

        return cls(item_number, item_name, item_format, divisor, units, format)

    def to_xml_tree(self):
        """
        Convert the ItemInfo instance to an XML ElementTree.

        Returns
        -------
        ElementTree.Element
            The XML ElementTree representing the ItemInfo instance.

        Notes
        -----
        This method converts the ItemInfo object into an XML blob
        using ElementTree.

        Examples
        --------
        >>> item_info_instance = ItemInfo(1, "Example", "Format", "1", "Units", "Format")
        >>> xml_tree = item_info_instance.to_xml_tree()
        >>> isinstance(xml_tree, ElementTree.Element)
        True
        """
        item_info_root = ElementTree.Element(
            "ItemInfo", attrib={"ItemNumber": str(self.item_number)}
        )

        item_name_element = ElementTree.SubElement(item_info_root, "ItemName")
        item_name_element.text = str(self.item_name)

        item_format_element = ElementTree.SubElement(item_info_root, "ItemFormat")
        item_format_element.text = str(self.item_format)

        divisor_element = ElementTree.SubElement(item_info_root, "Divisor")
        divisor_element.text = str(self.divisor)

        units_element = ElementTree.SubElement(item_info_root, "Units")
        units_element.text = str(self.units)

        format_element = ElementTree.SubElement(item_info_root, "Format")
        format_element.text = str(self.format)

        return item_info_root

    def __repr__(self):
        """Overwriting the __repr__ to mimic xml tree structure."""
        repr = f"""
        <ItemInfo ItemNumber="{self.item_number}">
            <ItemName>{self.item_name}</ItemName>
            <ItemFormat>{self.item_format}</ItemFormat>
            <Divisor>{self.divisor}</Divisor>
            <Units>{self.units}</Units>
            <Format>{self.format}</Format>
        </ItemInfo>
        """
        return re.sub(r"^\s*\n", "", repr, flags=re.MULTILINE)


class DataSource:
    """Data Source class."""

    def __init__(
        self,
        name: str,
        num_items: int,
        ts_type: str,
        data_type: str,
        interpolation: str,
        item_format: str,
        item_info: list[ItemInfo] | None = None,
    ):
        """
        Initialize a DataSource instance.

        Parameters
        ----------
        name : str
            The name of the data source.
        num_items : int
            The number of items in the data source.
        ts_type : str
            The time series type of the data source.
        data_type : str
            The data type of the data source.
        interpolation : str
            The interpolation method used by the data source.
        item_format : str
            The format of the items in the data source.
        item_info : list of ItemInfo or None, optional
            A list of ItemInfo objects providing additional information about items.
            Defaults to None.

        Returns
        -------
        None
        """
        self.name = name
        self.num_items = num_items
        self.ts_type = ts_type
        self.data_type = data_type
        self.interpolation = interpolation
        self.item_format = item_format
        if item_info is not None:
            self.item_info = item_info
        else:
            self.item_info = []

    @classmethod
    def from_xml(cls, source):
        """
        Create a DataSource instance from XML.

        Parameters
        ----------
        source : str or ElementTree.Element or bytes or bytearray or file-like object
            The XML source to parse and create a DataSource instance.

        Returns
        -------
        DataSource
            An instance of DataSource created from the XML source.

        Raises
        ------
        ValueError
            If the XML source type is not supported or if the XML structure is invalid.

        Notes
        -----
        This class method reads an object from XML, extracting information to create
        a DataSource instance.

        Examples
        --------
        >>> xml_string = "<DataSource Name='Example' NumItems='2'><TSType>...</TSType></DataSource>"
        >>> data_source_instance = DataSource.from_xml(xml_string)
        >>> isinstance(data_source_instance, DataSource)
        True
        """
        if isinstance(source, str):
            # If the source is a string, treat it as raw XML
            root = DefusedElementTree.fromstring(source)
        elif isinstance(source, ElementTree.Element):
            # If the source is an ElementTree object, use it directly
            root = source
        elif isinstance(source, bytes | bytearray):
            # If the source is a bytes or bytearray, assume it's
            # XML content and decode it.
            root = DefusedElementTree.fromstring(source.decode())
        elif hasattr(source, "read"):
            # If the source has a 'read' method, treat it as a
            # file-like object.
            root = DefusedElementTree.parse(source).getroot()
        else:
            raise ValueError("Unsupported XML source type.")

        if root.tag == "DataSource":
            name = root.attrib["Name"]
            num_items = int(root.attrib["NumItems"])
        else:
            raise ValueError(
                "Tag at DataSource level should be 'DataSource'," f" found {root.tag}."
            )

        ts_type = root.findtext("TSType")
        data_type = root.findtext("DataType")
        interpolation = root.findtext("Interpolation")
        item_format = root.findtext("ItemFormat")

        item_infos_raw = root.findall("ItemInfo")
        if (len(item_infos_raw) != num_items) and (num_items > 1):
            warnings.warn(
                f"Malformed Hilltop XML. DataSource {name} expects {num_items} "
                f"ItemInfo(s), but found {len(item_infos_raw)}",
                stacklevel=1,
            )

        # Hilltop sometimes sends more item infos than it actually has items.
        # To account for this we need to sort the item infos by item number,
        # then only select the first num_items item infos.

        item_info_list = []
        for info in item_infos_raw:
            item_info_list += [ItemInfo.from_xml(info)]

        info_dict = {}
        for item_info in item_info_list:
            info_dict[item_info.item_number] = item_info

        sorted_item_nums = sorted(list(info_dict.keys()))
        final_info_list = []
        if len(info_dict) > 0:
            for i in range(num_items):
                final_info_list += [info_dict[sorted_item_nums[i]]]
        else:
            final_info_list = []

        return cls(
            name,
            num_items,
            str(ts_type),
            str(data_type),
            str(interpolation),
            str(item_format),
            final_info_list,
        )

    def to_xml_tree(self):
        """
        Convert the DataSource instance to an XML ElementTree.

        Returns
        -------
        ElementTree.Element
            The XML ElementTree representing the DataSource instance.

        Notes
        -----
        This method converts the DataSource object into an XML blob
        using ElementTree.

        Examples
        --------
        >>> name = "Example"
        >>> num_items = 2
        >>> ts_type = "..."
        >>> data_type = "..."
        >>> interpolation = "..."
        >>> item_format = "..."
        >>> item_info = [ItemInfo(...), ItemInfo(...)]  # Replace '...' with appropriate arguments
        >>> data_source_instance = DataSource(name, num_items, ts_type, data_type, interpolation, item_format, item_info)
        >>> xml_tree = data_source_instance.to_xml_tree()
        >>> isinstance(xml_tree, ElementTree.Element)
        True
        """
        data_source_root = ElementTree.Element(
            "DataSource",
            attrib={"Name": self.name, "NumItems": str(self.num_items)},
        )

        ts_type_element = ElementTree.SubElement(data_source_root, "TSType")
        ts_type_element.text = str(self.ts_type)

        data_type_element = ElementTree.SubElement(data_source_root, "DataType")
        data_type_element.text = str(self.data_type)

        interpolation_element = ElementTree.SubElement(
            data_source_root, "Interpolation"
        )
        interpolation_element.text = str(self.interpolation)

        item_format_element = ElementTree.SubElement(data_source_root, "ItemFormat")
        item_format_element.text = str(self.item_format)

        if self.item_info is not None:
            data_source_root.extend(
                [element.to_xml_tree() for element in self.item_info]
            )
        return data_source_root

    def __repr__(self):
        """Overwriting the __repr__ to mimic xml tree structure."""
        repr = f"""
    <DataSource Name="{self.name}" NumItems="{self.num_items}">
        <TSType>{self.ts_type}</TSType>
        <DataType>{self.data_type}</DataType>
        <Interpolation>{self.interpolation}</Interpolation>
        <ItemFormat>{self.item_format}</ItemFormat>
        """
        for item in self.item_info:
            repr += f"""
{item}
            """
        repr += """
    </DataSource>
        """
        return re.sub(r"^\s*\n", "", repr, flags=re.MULTILINE)


class Data:
    """Data Class."""

    def __init__(
        self,
        date_format: str,
        num_items: int,
        timeseries: pd.DataFrame,
    ):
        """
        Initialize a Data instance.

        Parameters
        ----------
        date_format : str
            The date format associated with the data.
        num_items : int
            The number of items in the data.
        timeseries : pd.Series or pd.DataFrame
            The timeseries associated with the data. For a single-item data, a pd.Series
            is expected, and for multi-item data, a pd.DataFrame is expected.

        Returns
        -------
        None
        """
        self.date_format = date_format
        self.num_items = num_items
        self.timeseries = timeseries

    @classmethod
    def from_xml(cls, source):
        """
        Create a Data instance from XML.

        Parameters
        ----------
        source : str or ElementTree.Element or bytes or bytearray or file-like object
            The XML source to parse and create a Data instance.

        Returns
        -------
        Data
            An instance of Data created from the XML source.

        Raises
        ------
        ValueError
            If the XML source type is not supported or if the XML structure is invalid.

        Notes
        -----
        This class method reads an object from XML, extracting information to create
        a Data instance.

        Examples
        --------
        >>> xml_string = "<Data DateFormat='%Y-%m-%d' NumItems='1'><T>2023-01-01</T><V>42.0</V></Data>"
        >>> data_instance = Data.from_xml(xml_string)
        >>> isinstance(data_instance, Data)
        True
        """
        if isinstance(source, str):
            # If the source is a string, treat it as raw XML
            root = DefusedElementTree.fromstring(source)
        elif isinstance(source, ElementTree.Element):
            # If the source is an ElementTree object, use it directly
            root = source
        elif isinstance(source, bytes | bytearray):
            # If the source is a bytes or bytearray, assume it's
            # XML content and decode it.
            root = DefusedElementTree.fromstring(source.decode())
        elif hasattr(source, "read"):
            # If the source has a 'read' method, treat it as a
            # file-like object.
            root = DefusedElementTree.parse(source).getroot()
        else:
            raise ValueError("Unsupported XML source type.")

        if root.tag == "Data":
            date_format = root.attrib["DateFormat"]
            num_items = int(root.attrib["NumItems"])
        else:
            raise ValueError(
                "Tag at Data level should be 'Data'," f" found {root.tag}."
            )

        data_list = []
        for child in root:
            if child.tag == "E":
                data_dict = {}
                for element in child:
                    data_dict[element.tag] = element.text

                data_list += [data_dict]
            elif child.tag == "V":
                if child.text is not None:
                    timestamp, data_val = child.text.split(" ")
                    data_dict = {
                        "T": timestamp,
                        "V": data_val,
                    }
                    data_list += [data_dict]
            elif child.tag == "Gap":
                pass
            else:
                raise ValueError(
                    "Possibly Malformed XML: Data items not tagged with 'E' or 'V'."
                )

        timeseries = pd.DataFrame(data_list).set_index("T")
        return cls(date_format, num_items, timeseries)

    def to_xml_tree(self):
        """
        Convert the Data instance to an XML ElementTree.

        Returns
        -------
        ElementTree.Element
            The XML ElementTree representing the Data instance.

        Notes
        -----
        This method converts the Data object into an XML blob
        using ElementTree.

        Examples
        --------
        >>> date_format = "%Y-%m-%d"
        >>> num_items = 1
        >>> timeseries = pd.Series([42.0], index=["2023-01-01"])
        >>> data_instance = Data(date_format, num_items, timeseries)
        >>> xml_tree = data_instance.to_xml_tree()
        >>> isinstance(xml_tree, ElementTree.Element)
        True
        """
        data_root = ElementTree.Element(
            "Data",
            attrib={
                "DateFormat": self.date_format,
                "NumItems": str(self.num_items),
            },
        )

        for date, row in self.timeseries.iterrows():
            if (pd.isna(row).sum() == len(row)) or (sum(row.to_numpy() == "nan") > 0):
                # If all values in a row are NaNs, insert a Gap.
                element = ElementTree.SubElement(data_root, "Gap")
            else:
                element = ElementTree.SubElement(data_root, "E")
                timestamp = ElementTree.SubElement(element, "T")
                timestamp.text = str(date)
                for i, val in enumerate(row):
                    # If only one field in the element is a NaN, leave it blank?
                    val_item = ElementTree.SubElement(element, f"I{i+1}")
                    if not pd.isna(val):
                        val_item.text = str(val)

        # Collapse all duplicate Gap tags into a single Gap marker:
        current_gap_count = 0
        gaps_to_remove = []
        for elem in data_root:
            if elem.tag == "Gap":
                current_gap_count += 1
                if current_gap_count > 1:
                    gaps_to_remove.append(elem)
            else:
                current_gap_count = 0
        for gap in gaps_to_remove:
            data_root.remove(gap)

        return data_root

    def __repr__(self):
        """Overwriting the __repr__ to mimic xml tree structure."""
        repr = f"""
    <Data DateFormat="{self.date_format}" NumItems="{self.num_items}">
        """
        time = self.timeseries.index
        if isinstance(self.timeseries, pd.Series):
            repr += f"""
        <E>
            <T>{time[0]}</T>
            <I1>{self.timeseries.iloc[0]}</I1>
        </E>
            """
            if len(self.timeseries) > 2:
                repr += f"""
        ... [{len(self.timeseries) - 2} values omitted]
                """
            if len(self.timeseries) > 1:
                repr += f"""
        <E>
            <T>{time[-1]}</T>
            <I1>{self.timeseries.iloc[-1]}</I1>
        </E>
                """
        elif isinstance(self.timeseries, pd.DataFrame):
            repr += f"""
        <E>
            <T>{time[0]}</T>
            """
            for i in range(len(self.timeseries.columns)):
                repr += f"""
            <I{i+1}>{self.timeseries.iloc[0, i]}</I{i+1}>
                """
            repr += """
        </E>
            """
            if len(self.timeseries) > 2:
                repr += f"""
            ... [{len(self.timeseries) - 2} values omitted]
                """
            if len(self.timeseries) > 1:
                repr += f"""
        <E>
            <T>{time[-1]}</T>
                """
                for i in range(len(self.timeseries.columns)):
                    repr += f"""
            <I{i+1}>{self.timeseries.iloc[-1, i]}</I{i+1}>
                    """
            repr += """
        </E>
            """
        repr += """
    </Data>
        """
        return re.sub(r"^\s*\n", "", repr, flags=re.MULTILINE)


class DataSourceBlob:
    """DataSourceBlob class."""

    def __init__(
        self,
        site_name: str,
        data_source: DataSource,
        data: Data,
        tideda_site_number: str | None = None,
    ):
        """
        Initialize a DataSourceBlob instance.

        Parameters
        ----------
        site_name : str
            The name of the site associated with the data.
        data_source : DataSource
            The DataSource object containing information about the data source.
        data : Data
            The Data object containing the actual data.
        tideda_site_number : str or None, optional
            The Tideda site number, if available. Defaults to None.

        Returns
        -------
        None
        """
        self.site_name = site_name
        self.data_source = data_source
        self.data = data
        self.tideda_site_number = tideda_site_number

    @classmethod
    def from_xml(cls, source):
        """
        Create a DataSourceBlob instance from XML.

        Parameters
        ----------
        source : str or ElementTree.Element or bytes or bytearray or file-like object
            The XML source to parse and create a DataSourceBlob instance.

        Returns
        -------
        DataSourceBlob
            An instance of DataSourceBlob created from the XML source.

        Raises
        ------
        ValueError
            If the XML source type is not supported or if the XML structure is invalid.

        Notes
        -----
        This class method reads an object from XML, extracting information to create
        a DataSourceBlob instance.

        Examples
        --------
        >>> xml_string = "<Measurement SiteName='Example'><Data>...</Data></Measurement>"
        >>> data_source_blob = DataSourceBlob.from_xml(xml_string)
        >>> isinstance(data_source_blob, DataSourceBlob)
        True
        """
        if isinstance(source, str):
            # If the source is a string, treat it as raw XML
            root = DefusedElementTree.fromstring(source)
        elif isinstance(source, ElementTree.Element):
            # If the source is an ElementTree object, use it directly
            root = source
        elif isinstance(source, bytes | bytearray):
            # If the source is a bytes or bytearray, assume it's
            # XML content and decode it.
            root = DefusedElementTree.fromstring(source.decode())
        elif hasattr(source, "read"):
            # If the source has a 'read' method, treat it as a
            # file-like object.
            root = DefusedElementTree.parse(source).getroot()
        else:
            raise ValueError("Unsupported XML source type.")

        if root.tag == "Measurement":
            site_name = root.attrib["SiteName"]
        else:
            raise ValueError(
                "Tag at Measurement level should be 'Measurement',"
                f" found {root.tag}."
            )

        tideda_site_number = root.findtext("TidedaSiteNumber")

        data_source_element = root.find("DataSource")
        data_source = DataSource.from_xml(data_source_element)

        data_element = root.find("Data")
        data = Data.from_xml(data_element)

        return cls(site_name, data_source, data, tideda_site_number)

    def to_xml_tree(self):
        """
        Convert the DataSourceBlob instance to an XML ElementTree.

        Returns
        -------
        ElementTree.Element
            The XML ElementTree representing the DataSourceBlob instance.

        Notes
        -----
        This method converts the DataSourceBlob object into an XML blob
        using ElementTree.

        Examples
        --------
        >>> data_source_blob = DataSourceBlob("Example", data_source, data, "123")
        >>> xml_tree = data_source_blob.to_xml_tree()
        >>> isinstance(xml_tree, ElementTree.Element)
        True
        """
        data_source_blob_root = ElementTree.Element(
            "Measurement", attrib={"SiteName": self.site_name}
        )
        data_source_blob_root.append(self.data_source.to_xml_tree())
        if self.tideda_site_number is not None:
            tideda_site_number_element = ElementTree.SubElement(
                data_source_blob_root, "TidedaSiteNumber"
            )
            tideda_site_number_element.text = str(self.tideda_site_number)
        data_source_blob_root.append(self.data.to_xml_tree())

        return data_source_blob_root

    def __repr__(self):
        """Overwriting the __repr__ to mimic xml tree structure."""
        repr = f"""
<DataSourceBlob[Measurement] SiteName="{self.site_name}">
{self.data_source}
{self.data}
</DataSourceBlob[Measurement]">
        """
        return re.sub(r"^\s*\n", "", repr, flags=re.MULTILINE)


def parse_xml(source) -> list[DataSourceBlob]:
    """
    Parse Hilltop XML to get a list of DataSourceBlob objects.

    Parameters
    ----------
    source : str or ElementTree.Element or bytes or bytearray or file-like object
        The source XML to parse. It can be a raw XML string, an ElementTree object,
        XML content in bytes or bytearray, or a file-like object.

    Returns
    -------
    List[DataSourceBlob]
        A list of DataSourceBlob objects parsed from the Hilltop XML.

    Raises
    ------
    ValueError
        If the source type is not supported or if the XML structure is possibly malformed.

    Notes
    -----
    This function parses Hilltop XML and extracts information to create DataSourceBlob objects.
    The DataSourceBlob objects contain data from Measurement elements in the Hilltop XML.

    Examples
    --------
    >>> xml_string = "<Hilltop><Measurement>...</Measurement></Hilltop>"
    >>> data_source_blobs = parse_xml(xml_string)
    >>> len(data_source_blobs)
    1
    >>> isinstance(data_source_blobs[0], DataSourceBlob)
    True
    """
    if isinstance(source, str):
        # If the source is a string, treat it as raw XML
        root = DefusedElementTree.fromstring(source)
    elif isinstance(source, ElementTree.Element):
        # If the source is an Element object, use it directly as root
        root = source
    elif isinstance(source, ElementTree.ElementTree):
        # If the source is an ElementTree object, get the root
        root = source.getroot()
    elif isinstance(source, bytes | bytearray):
        # If the source is a bytes or bytearray, assume it's
        # XML content and decode it.
        root = DefusedElementTree.fromstring(source.decode())
    elif hasattr(source, "read"):
        # If the source has a 'read' method, treat it as a
        # file-like object.
        root = DefusedElementTree.parse(source).getroot()
    else:
        raise ValueError("Unsupported XML source type.")

    if root.tag == "HilltopServer":
        ElementTree.indent(root, space="\t")
        err_text = root.findtext("Error")
        if "No data" in str(err_text):
            warnings.warn(f"Empty hilltop response: {err_text}", stacklevel=1)
        else:
            raise ValueError(err_text)

    elif root.tag != "Hilltop":
        raise ValueError(
            f"Possibly malformed Hilltop xml. Root tag is '{root.tag}',"
            " should be 'Hilltop'."
        )
    data_source_blob_list = []
    for child in root.iter():
        if child.tag == "Measurement":
            data_source_blob = DataSourceBlob.from_xml(child)
            if (
                data_source_blob.data_source.item_info is not None
                and len(data_source_blob.data_source.item_info) > 0
            ):
                item_names = [
                    info.item_name for info in data_source_blob.data_source.item_info
                ]
                item_numbers = [
                    int(info.item_number)
                    for info in data_source_blob.data_source.item_info
                ]

                sorted_pairs = sorted(
                    zip(item_numbers, item_names, strict=True), key=lambda x: x[0]
                )
                sorted_items = sorted(
                    zip(
                        item_numbers,
                        data_source_blob.data_source.item_info,
                        strict=True,
                    ),
                    key=lambda x: x[0],
                )

                _, sorted_item_names = zip(*sorted_pairs, strict=True)
                _, sorted_item_list = zip(*sorted_items, strict=True)

                sorted_item_names = list(sorted_item_names)
                data_source_blob.data_source.item_info = list(sorted_item_list)

            else:
                sorted_item_names = []
            if len(sorted_item_names) > 0 and isinstance(
                data_source_blob.data.timeseries, pd.DataFrame
            ):
                cols = {
                    col: name
                    for col, name in zip(
                        data_source_blob.data.timeseries.columns,
                        sorted_item_names,
                        strict=True,
                    )
                }
                data_source_blob.data.timeseries = (
                    data_source_blob.data.timeseries.rename(columns=cols)
                )
            else:
                # It seems that if iteminfo is missing it's always a QC
                data_source_blob.data.timeseries = (
                    data_source_blob.data.timeseries.rename(columns={"I1": "Value"})
                )
            data_source_blob.data.timeseries.index.name = "Time"
            data_source_blob_list += [data_source_blob]

    return data_source_blob_list


def write_hilltop_xml(data_source_blob_list, output_path):
    """
    Write Hilltop XML file based on a list of DataSourceBlob objects.

    Parameters
    ----------
    data_source_blob_list : list[DataSourceBlob]
        List of DataSourceBlob objects to be included in the Hilltop XML file.
    output_path : str
        The path to the output XML file. If the file already exists, it will be overwritten.

    Returns
    -------
    None

    Raises
    ------
    ValueError
        If the data_source_blob_list is not a list of DataSourceBlob objects.

    Notes
    -----
    This function takes a list of DataSourceBlob objects and writes a Hilltop XML file
    using the ElementTree module. The resulting XML file follows the Hilltop schema.

    The XML file structure includes an 'Agency' element with the text content set to "Horizons",
    and then a series of elements generated from the DataSourceBlob objects in the provided list.
    The XML file is encoded in UTF-8, and it includes an XML declaration at the beginning.

    Examples
    --------
    >>> blob_list = [dataSourceBlob1, dataSourceBlob2, dataSourceBlob3]
    >>> write_hilltop_xml(blob_list, "output.xml")

    The above example writes a Hilltop XML file named "output.xml" based on the provided
    list of DataSourceBlob objects.

    """
    root = ElementTree.Element("Hilltop")
    agency = ElementTree.Element("Agency")
    agency.text = "Horizons"
    root.append(agency)

    for blob in data_source_blob_list:
        elem = blob.to_xml_tree()
        root.append(elem)

    ElementTree.indent(root, space="    ")
    etree = ElementTree.ElementTree(element=root)

    # Write the XML file to the specified output path
    etree.write(output_path, encoding="utf-8", xml_declaration=True)
