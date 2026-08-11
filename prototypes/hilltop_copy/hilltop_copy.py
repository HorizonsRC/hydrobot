"""Write data to a Hilltop file."""
from datetime import UTC, datetime

import numpy as np
import pandas as pd
import pythoncom
import pywintypes
import win32com.client
from win32com.client import VARIANT


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
        return

    def close(self):
        """
        Close the file - maybe.

        It appears to just call a bool, which shouldn't have an effect. However, there isn't enough documentation to
        say that this doesn't have a side effect that prevents a memory leak - so leaving this be for now. COM object
        bad. Returning it so that the linter doesn't complain.
        """
        return self.dput.Close

    # Write a Pandas Frame
    def put_std(self, df):
        """Insert Standard data into Hilltop COM."""
        if not self.dput.PutNew2(
            df.attrs["featureOfInterest"],
            df.attrs["procedure"],
            df.attrs["timeSeriesType"],
        ):
            raise RuntimeError(f"{self.dput.ErrorMsg}")
        if not df.attrs["timeSeriesType"] == 1:
            raise ValueError(
                f"Expected timeSeriesType=1 (Standard data), received timeSeriesType"
                f"={df.attrs['timeSeriesType']}"
            )

        for row in df.itertuples():
            if pd.isna(row.v):
                self.dput.PutGap()
                continue

            tm = row.Index.to_pydatetime()
            tm = tm.replace(tzinfo=UTC)  # Remove the time zone win32com hates it
            self.vtTime = tm
            self.vtValue = row.v
            self.dput.PutSingle(self.vtTime, self.vtValue)
            continue
        return

    def put_qual(self, df):
        """Insert Quality data into hilltop COM."""
        if not self.dput.PutNew2(
            df.attrs["featureOfInterest"],
            df.attrs["procedure"],
            df.attrs["timeSeriesType"],
        ):
            raise RuntimeError(f"{self.dput.ErrorMsg}")
        if not df.attrs["timeSeriesType"] == 2:
            raise ValueError(
                f"Expected timeSeriesType=2 (Quality data), received timeSeriesType"
                f"={df.attrs['timeSeriesType']}"
            )

        for row in df.itertuples():
            if pd.isna(row.v):
                self.dput.PutGap()
                continue

            tm = row.Index.to_pydatetime()
            tm = tm.replace(tzinfo=UTC)  # Remove the time zone win32com hates it
            self.vtTime = tm
            self.vtValue = row.v
            self.dput.PutSingle(self.vtTime, self.vtValue)
            continue
        return

    def put_check(self, df, data_type_list):
        """Insert check data into hilltop COM."""
        if not self.dput.PutNew2(
            df.attrs["featureOfInterest"],
            df.attrs["procedure"],
            df.attrs["timeSeriesType"],
        ):
            raise RuntimeError(f"{self.dput.ErrorMsg}")
        if not df.attrs["timeSeriesType"] == 3:
            raise ValueError(
                f"Expected timeSeriesType=3 (Check data), received timeSeriesType"
                f"={df.attrs['timeSeriesType']}"
            )

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

        def data_date_converter(data, info):
            if info == "D":
                return pd.to_datetime(data).to_pydatetime().replace(tzinfo=UTC)
            else:
                return data

        for row in df.itertuples():
            tm = row.Index.to_pydatetime()
            tm = tm.replace(tzinfo=UTC)  # Remove the time zone win32com hates it
            self.vtTime = tm
            self.vtValues = [
                data_date_converter(data, info)
                for (data, info) in zip(row[1:], data_type_list, strict=True)
            ]
            self.dput.PutArray(self.vtTime, self.vtValues)
            continue
        return


if __name__ == "__main__":
    htsfile = ToHilltop(r"output_dump\tester.hts")

    std_df = pd.DataFrame(
        [
            {
                "t": pd.to_datetime("20240303T10:00:00"),
                "v": 41,
            },
            {
                "t": pd.to_datetime("20240303T10:05:00"),
                "v": np.nan,
            },
            {
                "t": pd.to_datetime("20240303T10:10:00"),
                "v": 40,
            },
            {
                "t": pd.to_datetime("20240303T10:15:00"),
                "v": 42,
            },
        ]
    )
    std_df.attrs["featureOfInterest"] = "Example Site The Second"  # Site
    std_df.attrs["procedure"] = "Water Level"  # Datasource
    std_df.attrs["timeSeriesType"] = 1  # 1 = Standard Data
    std_df = std_df.set_index(std_df.t).drop(columns="t")

    qual_df = pd.DataFrame(
        [
            {
                "t": pd.to_datetime("20240303T10:00:00"),
                "v": 400,
            },
            {
                "t": pd.to_datetime("20240303T10:10:00"),
                "v": 600,
            },
        ]
    )
    qual_df.attrs["featureOfInterest"] = "Example Site The Second"  # Site
    qual_df.attrs["procedure"] = "Water Level"  # Datasource
    qual_df.attrs["timeSeriesType"] = 2  # 2 = Quality Data
    qual_df = qual_df.set_index(qual_df.t).drop(columns="t")

    check_df = pd.DataFrame(
        [
            {
                "t": pd.to_datetime("20240303T10:02:00"),  # Check time
                "v1": 42,  # Check value
                "v2": "20240303T10:02:00",  # Recorder time
                "v3": 43,
                "v4": "This is a comment",  # Comment
            },
            {
                "t": pd.to_datetime("20240303T10:13:00"),  # Check time
                "v1": 45,  # Check value
                "v2": "20240303T10:13:00",  # Recorder time
                "v3": 46,
                "v4": "This is another comment",  # Comment
            },
        ]
    )
    check_df.attrs["featureOfInterest"] = "Example Site The Second"  # Site
    check_df.attrs["procedure"] = "Water Level"  # Datasource
    check_df.attrs["timeSeriesType"] = 3  # 3 = Check Data
    check_df = check_df.set_index(check_df.t).drop(columns="t")

    check_data_types = ["I", "D", "I", "S"]

    htsfile.put_std(std_df)
    htsfile.put_qual(qual_df)
    htsfile.put_check(check_df, check_data_types)

    htsfile.close()
