"""Just a dummy script."""
import numpy as np
import pandas as pd
from annalist.annalist import Annalist

from hydrobot.plotter import check_plotter, gap_plotter

ann = Annalist()
ann.configure("Processing Water Temp Data.", "Hot Dameul, Sameul!")

gap_data_dict = pd.Series(
    {
        pd.Timestamp("2021-01-01 00:00"): 1.0,
        pd.Timestamp("2021-01-01 00:15"): 2.0,
        pd.Timestamp("2021-01-01 00:30"): np.NaN,
        pd.Timestamp("2021-01-01 00:45"): 1.0,
        pd.Timestamp("2021-01-01 01:00"): 5.0,
        pd.Timestamp("2021-01-01 01:15"): np.NaN,
        pd.Timestamp("2021-01-01 01:30"): np.NaN,
        pd.Timestamp("2021-01-01 01:45"): np.NaN,
        pd.Timestamp("2021-01-01 02:00"): 0.0,
        pd.Timestamp("2021-01-01 02:15"): 0.0,
        pd.Timestamp("2021-01-01 02:30"): 1.0,
        pd.Timestamp("2021-01-01 02:45"): 1.0,
    }
)

raw_data_dict = {
    pd.Timestamp("2021-01-01 00:00"): 1.0,
    pd.Timestamp("2021-01-01 01:00"): 5.0,
}

gap_plotter(gap_data_dict, 3)
check_plotter(gap_data_dict, raw_data_dict, 3)
