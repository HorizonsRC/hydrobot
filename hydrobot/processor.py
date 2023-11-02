"""Processor class."""

from annalist.annalist import Annalist
from hilltoppy import Hilltop

from hydrobot import filters

annalizer = Annalist()


class Processor(Hilltop):
    """docstring for Processor."""

    @annalizer.annalize
    def __init__(
        self,
        base_url: str,
        hts: str,
        site: str,
        measurement: str,
        timeout: int = 60,
        start: str | None = None,
        end: str | None = None,
        **kwargs,
    ):
        """Initialize a Processor instance."""
        super().__init__(base_url, hts, timeout, **kwargs)
        if site in self.available_sites:
            self._site = site
        else:
            raise ValueError(
                f"Site '{site}' not found for base_url and hts combo. "
                f"Available sites are {[s for s in self.available_sites]}"
            )

        self._measurement_list = self.get_measurement_list(site)
        if measurement in self._measurement_list.values:
            self._measurement = measurement
        else:
            raise ValueError(
                f"Measurement '{measurement}' not found at site '{site}'. "
                "Available measurements are "
                f"{[str(m[0]) for m in self._measurement_list.values]}"
            )

        self._start = start
        self._end = end
        self._stale = True

        # Load data for the first time
        self.reload_data()

    @property
    def start(self):
        """The start property."""
        return self._start

    @start.setter
    @annalizer.annalize
    def start(self, value):
        self._start = value
        self._stale = True

    @property
    def end(self):
        """The end property."""
        return self._end

    @end.setter
    @annalizer.annalize
    def end(self, value):
        self._end = value
        self._stale = True

    @property
    def dataset(self):
        """The dataset property."""
        return self._dataset

    @dataset.setter
    @annalizer.annalize
    def dataset(self, value):
        self._dataset = value

    @annalizer.annalize
    def reload_data(
        self,
        from_date: str | None = None,
        to_date: str | None = None,
        agg_method: str | None = None,
        agg_interval: str | None = None,
        alignment: str = "00:00",
        quality_codes: bool = False,
        apply_precision: bool = False,
        tstype: str | None = None,
    ):
        """(Re)Load Raw Data from Hilltop."""
        if from_date is None:
            from_date = self._start
        if to_date is None:
            to_date = self._end
        data = super().get_data(
            self._site,
            self._measurement,
            from_date=from_date,
            to_date=to_date,
            agg_method=agg_method,
            agg_interval=agg_interval,
            alignment=alignment,
            quality_codes=quality_codes,
            apply_precision=apply_precision,
            tstype=tstype,
        )
        self._dataset = data
        self._stale = False

    @annalizer.annalize
    def clip(self, low_clip: float, high_clip: float):
        """Clip data.

        Method implementation of filters.clip
        """
        data = self._dataset["Values"]
        return filters.clip(data, low_clip, high_clip)

    @annalizer.annalize
    def fbewma(self, span: int):
        """fbewma.

        Method implementation of filters.fbewma
        """
        data = self._dataset["Values"]
        return filters.fbewma(data, span)

    @annalizer.annalize
    def remove_outliers(self, span: int, delta: float):
        """Remove Outliers.

        Method implementation of filters.remove_outliers
        """
        data = self._dataset["Values"]
        return filters.remove_outliers(data, span, delta)

    @annalizer.annalize
    def remove_spikes(
        self,
        span: int,
        low_clip: float,
        high_clip: float,
        delta: float,
    ):
        """Remove Spikes.

        Method implementation of filters.remove_spikes
        """
        data = self._dataset["Values"]
        return filters.remove_spikes(data, span, low_clip, high_clip, delta)
