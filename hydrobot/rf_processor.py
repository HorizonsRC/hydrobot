"""Rainfall Processor Class."""

import warnings

import numpy as np
import pandas as pd
from annalist.annalist import Annalist
from annalist.decorators import ClassLogger

from hydrobot.processor import Processor, evaluator

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

    @ClassLogger
    def quality_encoder(
        self,
        gap_limit: int | None = None,
        max_qc: int | float | None = None,
        interval_dict: dict | None = None,
        supplemental_data: pd.Series | None = None,
    ):
        """
        Encode quality information in the quality series for a rainfall dataset.

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
        if gap_limit is None:
            gap_limit = (
                int(self._defaults["gap_limit"])
                if "gap_limit" in self._defaults
                else None
            )
        if max_qc is None:
            max_qc = self._defaults["max_qc"] if "max_qc" in self._defaults else np.NaN

        if interval_dict is None:
            interval_dict = self._interval_dict

        qc_checks = self.check_data[self.check_data["QC"]]
        qc_series = qc_checks["Value"] if "Value" in qc_checks else pd.Series({})

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
