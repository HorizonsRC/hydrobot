"""Dissolved oxygen utils."""


def correct_dissolved_oxygen(diss_ox, atm_pres, ap_altitude, do_altitude):
    """
    Corrects the dissolved oxygen.

    Only corrects for atmospheric pressure - that seems to be how we've done this for a while

    Parameters
    ----------
    diss_ox : pd.Series
        Dissolved oxygen uncorrected
    atm_pres : pd.Series
        Atmospheric pressure from nearby site
    ap_altitude : numeric
        Altitude of atmospheric pressure sensor (relative to sea level or w/e)
    do_altitude : numeric
        Altitude of dissolved oxygen sensor (relative to sea level or w/e, but make sure it's the same standard as
        altitude)

    Returns
    -------
    pd.Series
        Dissolved oxygen series, but corrected
    """
    atm_pres += (ap_altitude - do_altitude) * 0.1222

    # sea level atm pressure is 1013.25
    corr_diss_ox = diss_ox * 1013.25 / atm_pres
    return corr_diss_ox
