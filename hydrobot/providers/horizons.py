from datetime import datetime
from typing import Protocol
from hydrobot.providers.types import CheckData, StandardData, DataProviderError
from hydrobot.providers.protocol import DataProvider
from whurl.client import HilltopClient
from whurl.schemas.requests import GetDataRequest
from pydantic import BaseModel

class HorizonsProviderConfig(BaseModel):
    base_url: str
    hts: str

class HorizonsProvider(DataProvider):

    def __init__(
        self,
        config: HorizonsProviderConfig,
    ):
        self.config = config
        self.client = HilltopClient(
            base_url=config.base_url,
            hts_endpoint=config.hts,
        )

    def get_standard(
        self,
        site: str,
        measurement: str,
        from_date: datetime,
        to_date: datetime

    ) -> StandardData:
        """Return standard data and associated metadata."""

        with self.client:
            response = self.client.get_data(
                site=site,
                measurement=measurement,
                from_datetime=from_date,
                to_datetime=to_date,
                ts_type="StdSeries"
            )

        meas_found = False
        for meas in response.measurements:
            if meas.data_source.name == measurement:
                if meas_found:
                    raise DataProviderError(
                        "Multiple measurements returned when executing a "
                        f"get_standard call for {site} and {measurement}."
                    )

                df = meas.data.timeseries
                meas_found = True
                for info in meas.data_source.item_info:
                    if info.item_name == measurement:
                        standard_info = info

        metadata = {
            "item_name": standard_info.item_name,
            "item_format": standard_info.item_format,
            "divisor": standard_info.divisor,
            "units": standard_info.units,
            "format": standard_info.format
        }

        return StandardData(
            data=df,
            metadata=metadata,
        )

    def get_check(
        self,
        site: str,
        measurement: str,
        from_date: datetime,
        to_date: datetime,
    ) -> CheckData:
        """Return check data and associated metadata."""
        ...
        return CheckData(
            data=df,
            metadata=metadata,
        )

    def get_levels(
        self,
        site: str,

