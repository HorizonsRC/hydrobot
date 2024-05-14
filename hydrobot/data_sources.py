"""Handling for different types of data sources."""
import csv
from pathlib import Path

import numpy as np
import pandas as pd


class QualityCodeEvaluator:
    """Basic QualityCodeEvaluator only compares magnitude of differences."""

    def __init__(self, qc_500_limit, qc_600_limit, name="", constant_check_shift=0):
        """Initialize QualityCodeEvaluator.

        Parameters
        ----------
        qc_500_limit : numerical
            Threshold between QC 400 and QC 500
        qc_600_limit : numerical
            Threshold between QC 500 and QC 600
        name : str
            Name of the data source
        constant_check_shift : numerical
            Shifts the check data by a fixed amount
        """
        self.qc_500_limit = qc_500_limit
        self.qc_600_limit = qc_600_limit
        self.name = name
        self.constant_check_shift = constant_check_shift

    def __repr__(self):
        """QualityCodeEvaluator representation."""
        return repr(f"QualityCodeEvaluator '{self.name}'")

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
        name="",
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
        name : str
            Name of the data source
        constant_check_shift : numerical
            Shifts the check data by a fixed amount
        """
        QualityCodeEvaluator.__init__(
            self, qc_500_limit, qc_600_limit, name, constant_check_shift
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
        name="",
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
        name : str
            Name of the data source
        """
        QualityCodeEvaluator.__init__(
            self, qc_500_limit, qc_600_limit, name, constant_check_shift
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


def get_qc_evaluator_dict():
    """Return all qc_evaluators in a dictionary.

    Returns
    -------
    dict of string-qc_evaluator pairs
    """
    qc_evaluator_dict = {}
    script_dir = Path(__file__).parent
    # script_dir = os.path.dirname(os.path.abspath(__file__))

    # Plain QualityCodeEvaluators
    template_path = (script_dir / "config/QualityCodeEvaluator_QC_config.csv").resolve()
    with open(template_path) as csv_file:
        reader = csv.reader(csv_file)

        for row in reader:
            qc_evaluator_dict[row[0]] = QualityCodeEvaluator(
                float(row[1]), float(row[2]), row[0]
            )
        csv_file.close()

    # Two stage QualityCodeEvaluators
    template_path = (
        script_dir / "config/TwoLevelQualityCodeEvaluator_QC_config.csv"
    ).resolve()
    with open(template_path) as csv_file:
        reader = csv.reader(csv_file)

        for row in reader:
            qc_evaluator_dict[row[0]] = TwoLevelQualityCodeEvaluator(
                float(row[1]),
                float(row[2]),
                float(row[3]),
                float(row[4]),
                float(row[5]),
                row[0],
            )
        csv_file.close()

    # DO QualityCodeEvaluator
    template_path = (
        script_dir / "config/DissolvedOxygenQualityCodeEvaluator_QC_config.csv"
    ).resolve()
    with open(template_path) as csv_file:
        reader = csv.reader(csv_file)

        for row in reader:
            qc_evaluator_dict[row[0]] = DissolvedOxygenQualityCodeEvaluator(
                float(row[1]),
                float(row[2]),
                float(row[3]),
                float(row[4]),
                row[0],
            )
        csv_file.close()

    return qc_evaluator_dict


def get_qc_evaluator(qc_evaluator_name):
    """Return qc_evaluator that matches the given name.

    Raises exception if evaluator is not in the config.

    Parameters
    ----------
    qc_evaluator_name : string
        Name of the qc_evaluator as defined in the config

    Returns
    -------
    QualityCodeEvaluator
        The QualityCodeEvaluator class initiated with the standard config data
    """
    qce_dict = get_qc_evaluator_dict()
    if qc_evaluator_name in qce_dict:
        return qce_dict[qc_evaluator_name]
    raise Exception(
        f"qc_evaluator {qc_evaluator_name} not found in the config file. "
        f"Available qc_evaluators are {list(qce_dict.keys())}."
    )


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
    measurement_name: str,
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
    measurement_name : str
        measurement name
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
