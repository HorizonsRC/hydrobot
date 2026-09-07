"""Write data to a Hilltop file."""
import re
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd
import pythoncom
import pywintypes
import whurl
import win32com.client
from win32com.client import VARIANT


def _data_date_converter(df_row, info):
    if info == "D":
        return pd.to_datetime(df_row).to_pydatetime().replace(tzinfo=UTC)
    else:
        return df_row


def tstype_converter(ts_type: str) -> int:
    """
    Convert tstype strings into ints for COM interpretation.

    standard = 1
    quality = 2
    check = 3
    """
    match ts_type:
        case "StdSeries":
            return 1
        case "StdQualSeries":
            return 2
        case "CheckSeries":
            return 3
        case _:
            raise ValueError(f"Unrecognised ts_type: {ts_type}")


class ToHilltop:
    """
    Hilltop COM writer.

    Writes directly into a Hilltop file.
    """

    def __init__(self, output_hts):
        self.dput = win32com.client.Dispatch("Hilltop.DataInput")
        if not self.dput.open(output_hts):
            raise RuntimeError(f"No data file.  Error is: {self.dput.errormsg}")

        # Variants for receiving the date and values  They have to be initialised, not just declared.
        # We give a dummy date to get started
        self.vtTime = VARIANT(pythoncom.VT_DATE, pywintypes.Time(datetime(2024, 1, 1)))
        self.vtValue = VARIANT(pythoncom.VT_R4, 0.0)
        self.vtValues = VARIANT(
            pythoncom.VT_BYREF | pythoncom.VT_ARRAY | pythoncom.VT_VARIANT, []
        )

    def close(self):
        """
        Close the file - maybe.

        It appears to just call a bool, which shouldn't have an effect. However, there isn't enough documentation to
        say that this doesn't have a side effect that prevents a memory leak - so leaving this be for now. COM object
        bad. Returning it so that the linter doesn't complain.
        """
        return self.dput.Close

    def put_data(self, data_source_name, ts_type, item_info, site_name, data):
        """Insert data wrapper."""
        data.attrs["timeSeriesType"] = tstype_converter(ts_type)  # time series type
        data.attrs["featureOfInterest"] = site_name  # Site
        data.attrs["procedure"] = data_source_name  # Datasource
        if tstype_converter(ts_type) == 2:
            # Quality doesn't have item_info normally
            item_info = ["I"]

        self._put(data, item_info)

    # Write a Pandas Frame
    def put_std(self, df):
        """Insert Standard data into Hilltop COM."""
        df.attrs["timeSeriesType"] = 1
        self._put(df, ["F"])

    def put_qual(self, df):
        """Insert Quality data into hilltop COM."""
        df.attrs["timeSeriesType"] = 2
        self._put(df, ["I"])

    def put_check(self, df, data_type_list):
        """Insert check data into hilltop COM."""
        df.attrs["timeSeriesType"] = 3
        self._put(df, data_type_list)

    def _put(self, df, data_type_list):
        """Put data of arbitrary type to Hilltop via COM."""
        """Insert check data into hilltop COM."""
        if not self.dput.PutNew2(
            df.attrs["featureOfInterest"],
            df.attrs["procedure"],
            df.attrs["timeSeriesType"],
        ):
            raise RuntimeError(f"{self.dput.ErrorMsg}")

        if df.attrs["timeSeriesType"] not in [1, 2, 3]:
            raise ValueError(f"Invalid time series value {df.attrs['timeSeriesType']}")

        for data_type in data_type_list:
            known_data_types = ["F", "D", "S", "I"]  # float, date, string, integer
            if data_type not in known_data_types:
                raise ValueError(
                    f"Invalid data_type: {data_type}. Valid data types are {known_data_types}."
                )
        if len(data_type_list) != len(df.columns):
            raise ValueError(
                f"Received different number of data types and data columns. There are "
                f"{len(data_type_list)} data types given and {len(df.columns)} values in the data frame."
            )

        for row in df.itertuples():
            tm = row.Index.to_pydatetime()
            tm = tm.replace(tzinfo=UTC)  # Remove the time zone win32com hates it
            self.vtTime = tm
            self.vtValues = [
                _data_date_converter(data, info)
                for (data, info) in zip(row[1:], data_type_list, strict=True)
            ]
            self.dput.PutArray(self.vtTime, self.vtValues)


def read_hilltop_xml(xml):
    """Parse xml to turn it into write instructions for writing to hts."""
    with open(xml) as file:
        xml_content = file.read()
    root = whurl.schemas.responses.GetDataResponse.from_xml(xml_content)
    outputs = []
    for meas in root.measurement:
        meas_dict = {
            "data_source_name": meas.data_source.name,
            "ts_type": meas.data_source.ts_type,
            "item_info": [m.item_format for m in meas.data_source.item_info],
            "site_name": meas.site_name,
            "data": meas.data.timeseries,
        }
        outputs.append(meas_dict)
    return outputs


def read_hilltop_dsn(dsn):
    """Parse dsn to turn it into write instructions for writing to hts."""
    with open(dsn) as file:
        dsn_text = file.read()
    regex = re.compile(r'File\d*="(.*)"')
    source_file = regex.findall(dsn_text)
    outputs = []
    for path in source_file:
        print(path)
        if Path(path).suffix == ".dsn":
            outputs.append(read_hilltop_dsn(path))
        else:
            outputs.append(read_hilltop_xml(path))
    return outputs


if __name__ == "__main__":
    htsfile = ToHilltop(r"output_dump\tester.hts")
    qwe = read_hilltop_dsn(r".\output_dump\hydrobot_dsn.dsn")
    asd = read_hilltop_xml(r".\output_dump\processed_rf.xml")
    for q in qwe:
        htsfile.put_data(**q)
    htsfile.close()
