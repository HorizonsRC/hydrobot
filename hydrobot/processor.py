"""Processor class."""

import warnings
from functools import wraps

import pandas as pd
from annalist.annalist import Annalist
from annalist.decorators import ClassLogger
from hilltoppy import Hilltop

from hydrobot import data_acquisition, data_sources, evaluator, filters, plotter

annalizer = Annalist()


def stale_warning(method):
    """
    Decorate dangerous functions.

    Check whether the data is stale, and warn user if so.
    Warning will then take input form user to determine whether to proceed or cancel.
    Cancelling will return a null function, which returns None with no side effects no matter what the input

    Parameters
    ----------
    method : function
        A function that might have some problems if the parameters have been changed but the data hasn't been
        updated

    Returns
    -------
    function
        null function if warning is heeded, otherwise
    """

    @wraps(method)
    def _impl(self, *method_args, **method_kwargs):
        if self._stale:
            warnings.warn(
                "Warning: a key parameter of the data has changed but the data itself has not been reloaded."
            )
            while True:
                user_input = input("Do you want to continue? y/n: ")

                if user_input.lower() in ["y", "ye", "yes"]:
                    print("Continuing")
                    return method(self, *method_args, **method_kwargs)
                elif user_input.lower() in ["n", "no"]:
                    print("Function cancelled")
                    return lambda *x: None
                else:
                    print(
                        "Type y or n (or yes or no, or even ye, all ye who enter here)"
                    )
        else:
            return method(self, *method_args, **method_kwargs)

    return _impl


class Processor:
    """docstring for Processor."""

    @ClassLogger  # type: ignore
    def __init__(
        self,
        base_url: str,
        site: str,
        standard_hts: str,
        standard_measurement: str,
        frequency: str,
        from_date: str | None = None,
        to_date: str | None = None,
        check_hts: str | None = None,
        check_measurement: str | None = None,
        defaults: dict = {},
        **kwargs,
    ):
        """Initialize a Processor instance."""
        if check_hts is None:
            check_hts = standard_hts
        if check_measurement is None:
            check_measurement = standard_measurement

        standard_hilltop = Hilltop(base_url, standard_hts, **kwargs)
        check_hilltop = Hilltop(base_url, check_hts, **kwargs)
        if (
            site in standard_hilltop.available_sites
            and site in check_hilltop.available_sites
        ):
            self._site = site
        else:
            raise ValueError(
                f"Site '{site}' not found for both base_url and hts combos. "
                "Available sites in standard_hts are "
                f"{[s for s in standard_hilltop.available_sites]}. "
                "Available sites in check_hts are "
                f"{[s for s in check_hilltop.available_sites]}."
            )

        self._standard_measurement_list = standard_hilltop.get_measurement_list(site)
        if standard_measurement in self._standard_measurement_list.values:
            self._standard_measurement = standard_measurement
        else:
            raise ValueError(
                f"Standard measurement '{standard_measurement}' not found at"
                " site '{site}'. Available measurements are "
                f"{[str(m[0]) for m in self._standard_measurement_list.values]}"
            )
        self._check_measurement_list = check_hilltop.get_measurement_list(site)
        if check_measurement in self._check_measurement_list.values:
            self._check_measurement = check_measurement
        else:
            raise ValueError(
                f"Check measurement '{check_measurement}' not found at "
                f"site '{site}'. Available measurements are "
                f"{[str(m[0]) for m in self._check_measurement_list.values]}"
            )

        self._base_url = base_url
        self._standard_hts = standard_hts
        self._check_hts = check_hts
        self._frequency = frequency
        self._from_date = from_date
        self._to_date = to_date
        self._defaults = defaults
        self._measurement = data_sources.get_measurement(standard_measurement)

        self._stale = True
        self._standard_series = pd.Series({})
        self._check_series = pd.Series({})
        self._quality_series = pd.Series({})

        # Load data for the first time
        self.import_data()

    @property
    def site(self):
        """Site property."""
        return self._site

    @ClassLogger  # type: ignore
    @site.setter
    def site(self, value):
        self._site = value
        self._stale = True

    @property
    def from_date(self):
        """From_date property."""
        return self._from_date

    @ClassLogger  # type: ignore
    @from_date.setter
    def from_date(self, value):
        self._from_date = value
        self._stale = True

    @property
    def to_date(self):
        """To_date property."""
        return self._to_date

    @ClassLogger  # type: ignore
    @to_date.setter
    def to_date(self, value):
        self._to_date = value
        self._stale = True

    @property
    def frequency(self):
        """Frequency property."""
        return self._frequency

    @ClassLogger  # type: ignore
    @frequency.setter
    def frequency(self, value):
        self._frequency = value
        self._stale = True

    @property
    def base_url(self):
        """Base_url property."""
        return self._base_url

    @ClassLogger  # type: ignore
    @base_url.setter
    def base_url(self, value):
        self._base_url = value
        self._stale = True

    @property
    def standard_hts(self):
        """Standard_hts property."""
        return self._standard_hts

    @ClassLogger  # type: ignore
    @standard_hts.setter
    def standard_hts(self, value):
        self._standard_hts = value
        self._stale = True

    @property
    def check_hts(self):
        """Check_hts property."""
        return self._check_hts

    @ClassLogger  # type: ignore
    @check_hts.setter
    def check_hts(self, value):
        self._check_hts = value
        self._stale = True

    @property
    def measurement(self):
        """Measurement property."""
        return self._measurement

    @ClassLogger  # type: ignore
    @measurement.setter
    def measurement(self, value):
        self._measurement = value
        self._stale = True

    @property
    def defaults(self):
        """Defaults property."""
        return self._defaults

    @ClassLogger  # type: ignore
    @defaults.setter
    def defaults(self, value):
        self._defaults = value
        self._stale = True

    @property  # type: ignore
    def standard_series(self):  # type: ignore
        """Standard dataset property."""  # type: ignore
        return self._standard_series  # type: ignore

    @ClassLogger  # type: ignore
    @standard_series.setter  # type: ignore
    def standard_series(self, value):  # type: ignore
        self._standard_series = value  # type: ignore

    @property
    def check_series(self):
        """Check dataset property."""
        return self._check_series

    @ClassLogger  # type: ignore
    @check_series.setter
    def check_series(self, value):
        self._check_series = value

    @property
    def quality_series(self):
        """Quality dataset property."""
        return self._quality_series

    @ClassLogger  # type: ignore
    @quality_series.setter
    def quality_series(self, value):
        self._quality_series = value
        self._stale = True

    @ClassLogger
    def import_range(
        self,
        from_date: str | None,
        to_date: str | None,
        standard: bool = True,
        check: bool = True,
        quality: bool = False,
    ):
        """Load Raw Data from Hilltop."""
        if standard:
            insert_series = data_acquisition.get_series(
                self._base_url,
                self._standard_hts,
                self._site,
                self._standard_measurement,
                from_date,
                to_date,
                tstype="Standard",
            )
            insert_series = insert_series.asfreq(self.frequency, method="bfill")
            slice_to_remove = self.standard_series.loc[
                insert_series.index[0] : insert_series.index[-1]
            ]
            cleaned_series = self.standard_series.drop(slice_to_remove.index)
            self.standard_series = pd.concat(
                [
                    cleaned_series if not cleaned_series.empty else None,
                    insert_series if not insert_series.empty else None,
                ]
            ).sort_index()
        if check:
            insert_series = data_acquisition.get_series(
                self._base_url,
                self._check_hts,
                self._site,
                self._check_measurement,
                from_date,
                to_date,
                tstype="Check",
            )
            slice_to_remove = self.check_series.loc[
                insert_series.index[0] : insert_series.index[-1]
            ]
            cleaned_series = self.check_series.drop(slice_to_remove.index)
            self.check_series = pd.concat(
                [
                    cleaned_series if not cleaned_series.empty else None,
                    insert_series if not insert_series.empty else None,
                ]
            ).sort_index()
        if quality:
            insert_series = data_acquisition.get_series(
                self._base_url,
                self._standard_hts,
                self._site,
                self._standard_measurement,
                from_date,
                to_date,
                tstype="Quality",
            )
            slice_to_remove = self.quality_series.loc[
                insert_series.index[0] : insert_series.index[-1]
            ]
            cleaned_series = self.quality_series.drop(slice_to_remove.index)
            self.quality_series = pd.concat(
                [cleaned_series, insert_series]
            ).sort_index()

    def import_data(
        self,
        standard: bool = True,
        check: bool = True,
        quality: bool = False,
    ):
        """Import data using class parameter range."""
        self.import_range(self._from_date, self._to_date, standard, check, quality)
        self._stale = False

    # @stale_warning  # type: ignore
    @ClassLogger
    def gap_closer(self, gap_limit: int | None = None):
        """Gap closer implementation."""
        if gap_limit is None:
            gap_limit = self._defaults["gap_limit"]
        self.standard_series = evaluator.small_gap_closer(
            self._standard_series, gap_limit=gap_limit
        )

    # @stale_warning  # type: ignore
    @ClassLogger
    def quality_encoder(self, gap_limit: int | None = None):
        """Gap closer implementation."""
        if gap_limit is None:
            gap_limit = self._defaults["gap_limit"]
        self.quality_series = evaluator.quality_encoder(
            self._standard_series,
            self._check_series,
            self._measurement,
            gap_limit=gap_limit,
        )

    # @stale_warning  # type: ignore
    @ClassLogger
    def clip(self, low_clip: float | None = None, high_clip: float | None = None):
        """Clip data.

        Method implementation of filters.clip
        """
        if low_clip is None:
            low_clip = self._defaults["low_clip"]
        if high_clip is None:
            high_clip = self._defaults["high_clip"]

        self.standard_series = filters.clip(self._standard_series, low_clip, high_clip)
        self.check_series = filters.clip(self._check_series, low_clip, high_clip)

    # @stale_warning  # type: ignore
    @ClassLogger
    def remove_outliers(self, span: int | None = None, delta: float | None = None):
        """Remove Outliers.

        Method implementation of filters.remove_outliers
        """
        if span is None:
            span = self._defaults["span"]
        if delta is None:
            delta = self._defaults["delta"]

        self.standard_series = filters.remove_outliers(
            self._standard_series, span, delta
        )

    # @stale_warning  # type: ignore
    @ClassLogger
    def remove_spikes(
        self,
        low_clip: float | None = None,
        high_clip: float | None = None,
        span: int | None = None,
        delta: float | None = None,
    ):
        """Remove Spikes.

        Method implementation of filters.remove_spikes
        """
        if low_clip is None:
            low_clip = self._defaults["low_clip"]
        if high_clip is None:
            high_clip = self._defaults["high_clip"]
        if span is None:
            span = self._defaults["span"]
        if delta is None:
            delta = self._defaults["delta"]
        self.standard_series = filters.remove_spikes(
            self._standard_series, span, low_clip, high_clip, delta
        )

    @ClassLogger
    def data_exporter(self, file_location):
        """Export data to csv."""
        data_sources.series_export_to_csv(
            file_location,
            self._site,
            self._measurement.name,
            self._standard_series,
            self._check_series,
            self._quality_series,
        )

    def diagnosis(self):
        """Describe the state of the data."""
        evaluator.diagnose_data(
            self._standard_series,
            self._check_series,
            self._quality_series,
            self._frequency,
        )

    def plot_qc_series(self, show=True):
        """Implement qc_plotter()."""
        plotter.qc_plotter(
            self._standard_series,
            self._check_series,
            self._quality_series,
            self._frequency,
            show=show,
        )

    def plot_gaps(self, span=None, show=True):
        """Implement gap_plotter()."""
        if span is None:
            plotter.gap_plotter(self._standard_series, show=show)
        else:
            plotter.gap_plotter(self._standard_series, span, show=show)

    def plot_checks(self, span=None, show=True):
        """Implement check_plotter()."""
        if span is None:
            plotter.check_plotter(self._standard_series, self._check_series, show=show)
        else:
            plotter.check_plotter(
                self._standard_series, self._check_series, span, show=show
            )
