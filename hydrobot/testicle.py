"""Minimal reproduction of possible bug."""
import pandas as pd

DEFAULTS = {
    "a": 2.4,
    "b": 0.5,
}


class TestClass:
    """Test Class."""

    def __init__(self, default_values: dict):
        """TestClass constructor."""
        # This code lints just fine:
        if default_values is None:
            self._defaults = DEFAULTS
        else:
            self._defaults = default_values

        # This code gives linting error:
        # if default_values is None:
        #     default_values = DEFAULTS
        # self._defaults = default_values

    def class_wrapper(self, a: float | None = None):
        """Wrap dothething."""
        if a is None:
            a = self._defaults["a"]

        return dothething(a)


def dothething(a: float):
    """Do the thing."""
    return a**a


raw_data_dict = {
    pd.Timestamp("2021-01-01 00:00"): 1.0,
    pd.Timestamp("2021-01-01 00:15"): 2.0,
    pd.Timestamp("2021-01-01 00:30"): 10.0,
    pd.Timestamp("2021-01-01 00:45"): 4.0,
    pd.Timestamp("2021-01-01 01:00"): 5.0,
}
