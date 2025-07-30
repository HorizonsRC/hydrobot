"""Handling for different types of data sources."""

import numpy as np
import pandas as pd

DATA_FAMILY_DICT = {
    "Dissolved_Oxygen": {
        "QC_evaluator_type": "DO",
        "QC_evaluator_values": [6, 3, 0.1, 0.05],
        "Processor_type": "DO",
    },
    "Water_Temperature": {
        "QC_evaluator_type": "Base",
        "QC_evaluator_values": [1.2, 0.8],
        "Processor_type": "Base",
    },
    "Atmospheric_Pressure": {
        "QC_evaluator_type": "Base",
        "QC_evaluator_values": [5, 2.5],
        "Processor_type": "Base",
    },
    "Rainfall": {
        "QC_evaluator_type": "Base",
        "QC_evaluator_values": [20, 10],
        "Processor_type": "RF",
    },
    "Stage": {
        "QC_evaluator_type": "TwoLevel",
        "QC_evaluator_values": [10, 3, 0.5, 0.2, 2000],
        "Processor_type": "Base",
    },
    "Groundwater": {
        "QC_evaluator_type": "Base",
        "QC_evaluator_values": [20, 10],
        "Processor_type": "Base",
    },
    "pH": {
        "QC_evaluator_type": "BaseWith200",
        "QC_evaluator_values": [0.5, 0.2, 0.8],
        "Processor_type": "Base",
    },
    "Conductivity": {
        "QC_evaluator_type": "BaseWith200",
        "QC_evaluator_values": [10, 3, 15],
        "Processor_type": "Base",
    },
    "BG_Algae": {
        "QC_evaluator_type": "Unchecked",
        "QC_evaluator_values": [],
        "Processor_type": "Base",
    },
    "ORP": {
        "QC_evaluator_type": "Unchecked",
        "QC_evaluator_values": [],
        "Processor_type": "Base",
    },
    "Unchecked": {
        "QC_evaluator_type": "Unchecked",
        "QC_evaluator_values": [],
        "Processor_type": "Base",
    },
}


def depth_standard_measurement_name_by_data_family(data_family, depth):
    """
    Returns standard measurement name for the data family at depth.

    Many data sources have separate measurement name formats for lake sampling,
    so this maps the data_family/depth to the appropriate standard measurement name

    Parameters
    ----------
    data_family : str
        data family to find standard measurement name for
    depth : int
        depth of the measurement, in mm

    Returns
    -------
    str
        The standard measurement name
    """
    match data_family:
        case "pH":
            return f"pH (-{str(depth)} mm)"
        case "ORP":
            return f"ORP (-{str(depth)} mm)"
        case _:
            raise ValueError(f"Unimplemented depth data family {data_family}. ")


def depth_check_measurement_name_by_data_family(data_family, depth):
    """
    Returns check measurement name for the data family at depth.

    Many data sources have separate measurement name formats for lake sampling,
    so this maps the data_family/depth to the appropriate check measurement name

    Parameters
    ----------
    data_family : str
        data family to find check measurement name for
    depth : int
        depth of the measurement, in mm

    Returns
    -------
    str
        The check measurement name
    """
    match data_family:
        case "pH":
            return f"pH Check (-{str(depth)} mm)"
        case "ORP":
            return f"ORP Check  (-{str(depth)} mm)"
        case _:
            raise ValueError(
                f"Unimplemented depth data family {data_family}. Either remove depth as parameter or "
                f"implement "
            )


class QualityCodeEvaluator:
    """Basic QualityCodeEvaluator only compares magnitude of differences."""

    def __init__(self, qc_500_limit, qc_600_limit, constant_check_shift=0):
        """Initialize QualityCodeEvaluator.

        Parameters
        ----------
        qc_500_limit : numerical
            Threshold between QC 400 and QC 500
        qc_600_limit : numerical
            Threshold between QC 500 and QC 600
        constant_check_shift : numerical
            Shifts the check data by a fixed amount
        """
        self.qc_500_limit = qc_500_limit
        self.qc_600_limit = qc_600_limit
        self.constant_check_shift = constant_check_shift

    def __repr__(self):
        """QualityCodeEvaluator representation."""
        return repr(
            f"QualityCodeEvaluator or it's child: '{self.__class__.__name__}' with attributes: {self.__dict__}"
        )

    def find_qc(self, base_datum, check_datum):
        """
        Find the base quality codes.

        Parameters
        ----------
        base_datum : numerical
            Closest continuum datum point to the check
        check_datum : numerical
            The check data to verify the continuous data, shifted by any constant_check_shift

        Returns
        -------
        int
            The Quality code

        """
        check_datum = check_datum + self.constant_check_shift
        diff = np.abs(base_datum - check_datum)
        if diff < self.qc_600_limit:
            qc = 600
        elif diff < self.qc_500_limit:
            qc = 500
        else:
            qc = 400

        return qc


class TwoLevelQualityCodeEvaluator(QualityCodeEvaluator):
    """QualityCodeEvaluator for standards such as water level.

    Fixed error up to given threshold, percentage error after that.
    """

    def __init__(
        self,
        qc_500_limit,
        qc_600_limit,
        qc_500_percent,
        qc_600_percent,
        limit_percent_threshold,
        constant_check_shift=0,
    ):
        """
        Initialize TwoLevelQualityCodeEvaluator.

        Parameters
        ----------
        qc_500_limit : numerical
            Threshold between QC 400 and QC 500 for linear portion
        qc_600_limit : numerical
            Threshold between QC 500 and QC 600 for linear portion
        qc_500_percent : numerical
            Threshold between QC 400 and QC 500 for percentage portion
        qc_600_percent : numerical
            Threshold between QC 500 and QC 600 for percentage portion
        limit_percent_threshold
            Value at which the evaluator transitions between linear and percentage
            QC comparison
        constant_check_shift : numerical
            Shifts the check data by a fixed amount
        """
        QualityCodeEvaluator.__init__(
            self, qc_500_limit, qc_600_limit, constant_check_shift
        )
        self.qc_500_percent = qc_500_percent
        self.qc_600_percent = qc_600_percent
        self.limit_percent_threshold = limit_percent_threshold

    def find_qc(self, base_datum, check_datum):
        """Find the base quality codes with two stages.

        The two stages are: a flat and percentage QC threshold.

        Parameters
        ----------
        base_datum : numerical
            Closest continuum datum point to the check
        check_datum : numerical
            The check data to verify the continuous data, shifted by any constant_check_shift

        Returns
        -------
        int
            The Quality code

        """
        check_datum = check_datum + self.constant_check_shift
        if base_datum < self.limit_percent_threshold:
            # flat qc check
            diff = np.abs(base_datum - check_datum)
            if diff < self.qc_600_limit:
                qc = 600
            elif diff < self.qc_500_limit:
                qc = 500
            else:
                qc = 400
        else:
            # percent qc check
            diff = np.abs(base_datum / check_datum - 1) * 100
            if diff < self.qc_600_percent:
                qc = 600
            elif diff < self.qc_500_percent:
                qc = 500
            else:
                qc = 400
        return qc


class With200QualityCodeEvaluator(QualityCodeEvaluator):
    """For standard quality code evaluators that also have QC200 data.

    Examples: pH and Conductivity.
    """

    def __init__(
        self,
        qc_500_limit,
        qc_600_limit,
        qc_400_limit,
        constant_check_shift=0,
    ):
        """
        Initialize TwoLevelQualityCodeEvaluator.

        Parameters
        ----------
        qc_500_limit : numerical
            Threshold between QC 400 and QC 500
        qc_600_limit : numerical
            Threshold between QC 500 and QC 600
        qc_400_limit : numerical
            Threshold between QC 200 and QC 400
        constant_check_shift : numerical
            Shifts the check data by a fixed amount
        """
        QualityCodeEvaluator.__init__(
            self, qc_500_limit, qc_600_limit, constant_check_shift
        )
        self.qc_400_limit = qc_400_limit

    def find_qc(self, base_datum, check_datum):
        """
        Find the base quality codes.

        Parameters
        ----------
        base_datum : numerical
            Closest continuum datum point to the check
        check_datum : numerical
            The check data to verify the continuous data, shifted by any constant_check_shift

        Returns
        -------
        int
            The Quality code

        """
        check_datum = check_datum + self.constant_check_shift
        diff = np.abs(base_datum - check_datum)
        if diff < self.qc_600_limit:
            qc = 600
        elif diff < self.qc_500_limit:
            qc = 500
        elif diff < self.qc_400_limit:
            qc = 400
        else:
            qc = 200

        return qc


class UncheckedQualityCodeEvaluator(QualityCodeEvaluator):
    """QualityCodeEvaluator for data without checks.

    Returns 200 for QC.
    """

    def __init__(
        self,
    ):
        """Initialize UncheckedQualityCodeEvaluator."""
        QualityCodeEvaluator.__init__(self, -1, -2)

    def find_qc(self, base_datum, check_datum):
        """
        Return 200 quality code.

        Parameters
        ----------
        base_datum : numerical
            Closest continuum datum point to the check
        check_datum : numerical
            The check data to verify the continuous data, shifted by any constant_check_shift

        Returns
        -------
        int
            The Quality code 200

        """
        return 200


class DissolvedOxygenQualityCodeEvaluator(QualityCodeEvaluator):
    """QualityCodeEvaluator for DO NEMS.

    Constant error plus percentage error.
    """

    def __init__(
        self,
        qc_500_limit,
        qc_600_limit,
        qc_500_percent,
        qc_600_percent,
        constant_check_shift=0,
    ):
        """
        Initialize TwoLevelQualityCodeEvaluator.

        Parameters
        ----------
        qc_500_limit : numerical
            Constant contribution to QC 500 limit
        qc_600_limit : numerical
            Constant contribution to QC 600 limit
        qc_500_percent : numerical
            Variable contribution to QC 500 limit
        qc_600_percent : numerical
            Variable contribution to QC 600 limit
        """
        QualityCodeEvaluator.__init__(
            self, qc_500_limit, qc_600_limit, constant_check_shift
        )
        self.qc_500_percent = qc_500_percent
        self.qc_600_percent = qc_600_percent

    def find_qc(self, base_datum, check_datum):
        """Find the base quality codes for DO.

        Parameters
        ----------
        base_datum : numerical
            Closest continuum datum point to the check
        check_datum : numerical
            The check data to verify the continuous data, shifted by any constant_check_shift

        Returns
        -------
        int
            The Quality code

        """
        check_datum = check_datum + self.constant_check_shift

        diff = np.abs(base_datum - check_datum)
        threshold_500 = self.qc_500_limit + self.qc_500_percent * base_datum
        threshold_600 = self.qc_600_limit + self.qc_600_percent * base_datum
        if diff < threshold_600:
            qc = 600
        elif diff < threshold_500:
            qc = 500
        else:
            qc = 400
        return qc


def series_export_to_csv(
    file_location: str,
    series: list[pd.Series],
) -> None:
    """Export the 3 main series to csv.

    Parameters
    ----------
    file_location : str
        Where the files are exported to
    series : pd.Series
        Pandas series to be exported

    Returns
    -------
    None, but makes files
    """
    export_df = pd.DataFrame(series).T
    export_df.to_csv(str(file_location))


def hilltop_export(
    file_location: str,
    site_name: str,
    std_series: pd.Series,
    check_series: pd.Series,
    qc_series: pd.Series,
):
    """
    Export the 3 main series to csv files ready to import into hilltop.

    Parameters
    ----------
    file_location : str
        Where the files are exported to
    site_name : str
        Site name
    std_series : pd.Series
        Standard series
    check_series : pd.Series
        Check series
    qc_series : pd.Series
        Quality code series

    Returns
    -------
    None, but makes files
    """
    qc_series = qc_series.reindex(std_series.index, method="ffill")
    std_series.name = "std"
    qc_series.name = "qual"
    export_df = std_series.to_frame().join(qc_series)
    export_df.to_csv(str(file_location) + "_std_qc.csv")

    keys = [
        "Sitename",
        "Inspection_Date",
        "Inspection_Time",
        "External S.G.",
        "Recorder Time",
        "Internal S.G.",
        "Comment",
    ]

    export_check_df = pd.concat(
        [
            pd.Series(site_name, index=check_series.index),
            pd.Series(
                [str(dt.date()) for dt in check_series.index], index=check_series.index
            ),
            pd.Series(
                [str(dt.time()) for dt in check_series.index], index=check_series.index
            ),
            check_series,
            pd.Series(check_series.index, index=check_series.index),
            pd.Series(-1, index=check_series.index),
            pd.Series("hydrobot comment", index=check_series.index),
        ],
        axis=1,
        keys=keys,
    )

    export_check_df.to_csv(str(file_location) + "_check.csv")


def get_qc_evaluator(family: str):
    """Get QC evaluator from data family name."""
    qc_string = DATA_FAMILY_DICT[family]["QC_evaluator_type"]
    match qc_string:
        case "Base":
            qc_evaluator = QualityCodeEvaluator
        case "BaseWith200":
            qc_evaluator = With200QualityCodeEvaluator
        case "TwoLevel":
            qc_evaluator = TwoLevelQualityCodeEvaluator
        case "DO":
            qc_evaluator = DissolvedOxygenQualityCodeEvaluator
        case "Unchecked":
            qc_evaluator = UncheckedQualityCodeEvaluator
        case _:
            raise KeyError(f"QC_evaluator: {qc_string} has not been implemented yet")
    qc_evaluator = qc_evaluator(*DATA_FAMILY_DICT[family]["QC_evaluator_values"])
    return qc_evaluator
