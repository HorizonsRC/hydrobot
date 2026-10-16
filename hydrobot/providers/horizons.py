from datetime import datetime
from typing import Protocol
from hydrobot.providers.types import CheckData, StandardData, DataProviderError
from hydrobot.providers.protocol import DataProvider
from whurl.client import HilltopClient
from whurl.schemas.requests import GetDataRequest
from pydantic import BaseModel
import pandas as pd
from hydrobot.orchestration.resume import resume_point

class HorizonsProviderConfig(BaseModel):
    base_url: str
    standard_hts_filename: str
    check_hts_filename: str
    # The archive is optional: only last_processed_time needs it (so far).
    archive_base_url: str | None = None
    archive_standard_hts_filename: str | None = None
    archive_check_hts_filename: str | None = None

class HorizonsProvider:
    """Hilltop-backed provider for Horizons.

    Deliberately does NOT subclass DataProvider: a subclass would inherit the
    Protocol's ``...`` bodies, so a forgotten method would silently return
    ``None``. tests/test_providers/test_horizons.py checks conformance instead.
    """

    def __init__(
        self,
        config: HorizonsProviderConfig,
    ):
        self.config = config
        self.client = HilltopClient(
            base_url=config.base_url,
            hts_endpoint=config.standard_hts_filename,
        )
        self.check_client = HilltopClient(
            base_url=config.base_url,
            hts_endpoint=config.check_hts_filename,
        )
        self.archive_client = None
        if config.archive_base_url and config.archive_standard_hts_filename:
            self.archive_client = HilltopClient(
                base_url=config.archive_base_url,
                hts_endpoint=config.archive_standard_hts_filename,
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

    def last_processed_time(self, site: str, measurement: str) -> datetime | None:
        """Return when processing should resume, or None if never archived.

        A GetData with no time range returns only the latest point. So we ask
        for the latest quality entry first, then fetch the standard data (with
        quality) form that time on, so trailing points that were copied up
        without being processed can be recognised and ignored.
        """
        if self.archive_client is None:
            raise DataProviderError(
                "last_processed_time needs archive_base_url and "
                "archive_standard_hts_filename in provider_params."
            )

        with self.archive_client as archive:
            qual_resp = archive.get_data(
                site=site, measurement=measurement, ts_type="StdQualSeries"
            )
            qual = _quality_series(_timeseries(qual_resp, site, measurement))

            from_kwargs = {}
            if not qual.empty:
                from_kwargs["from_datetime"] = qual.index.max().to_pydatetime()

            std_resp = archive.get_data(
                site=site,
                measurement=measurement,
                ts_type="StdSeries",
                show_quality="Yes",
                **from_kwargs,
            )
            std = _timeseries(std_resp, site, measurement)

        if not std.empty and "Quality" not in std.columns:
            raise DataProviderError(
                "Archive standard data has no 'Quality' column; "
                f"got {list(std.columns)}."
            )

        result = resume_point(std, qual)

        return None if result is None else result.to_pydatetime()

def _timeseries(response, site: str, measurement: str) -> pd.DataFrame:
    """The single matching timeseries in a response; empty if none."""
    found = [m for m in response.measurements if m.data_source.name == measurement]
    if len(found) > 1:
        raise DataProviderError(
            f"Multiple measurement returned for {site} and {measurement}."
        )
    return found[0].data.timeseries if found else pd.DataFrame()

def _quality_series(df: pd.DataFrame) -> pd.Series:
    """A StdQualSeries frame (one column of quality codes) as a Series."""
    if df.empty:
        return pd.Series(dtype=float, name="Quality")
    if df.shape[1] != 1:
        raise DataProviderError(
            f"Expected a single quality column; got {list(df.columns)}."
        )
    return df.iloc[:, 0].astype(float).rename("Quality")

