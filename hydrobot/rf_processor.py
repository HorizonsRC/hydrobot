"""Rainfall Processor Class."""


from hydrobot.processor import (
    Processor,
)


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
