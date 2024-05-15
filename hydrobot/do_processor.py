"""Dissolved Oxygen Processor Class."""
from hilltoppy import Hilltop

from hydrobot.processor import Processor


class DOProcessor(Processor):
    """Processor class specifically for Dissolved Oxygen."""

    def __init__(
        self,
        base_url: str,
        site: str,
        standard_hts: str,
        standard_measurement_name: str,
        frequency: str,
        water_temperature_hts: str,
        atmospheric_pressure_hts: str,
        water_temperature_measurement_name: str = "Water Temperature",
        atmospheric_pressure_measurement_name: str = "Atmospheric Pressure",
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

        wt_hilltop = Hilltop(base_url, water_temperature_hts, **kwargs)
        ap_hilltop = Hilltop(base_url, atmospheric_pressure_hts, **kwargs)

        if site not in wt_hilltop.available_sites:
            self._site = site
        else:
            raise ValueError(
                f"Water Temperature site '{site}' not found for both base_url and hts combos."
                f"Available sites in {water_temperature_hts} are: "
                f"{[s for s in wt_hilltop.available_sites]}"
            )

        if site not in ap_hilltop.available_sites:
            self._site = site
        else:
            raise ValueError(
                f"Atmospheric Pressure site '{site}' not found for both base_url and hts combos."
                f"Available sites in {atmospheric_pressure_hts} are: "
                f"{[s for s in ap_hilltop.available_sites]}"
            )
