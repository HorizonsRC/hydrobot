"""Decide where processing should resume, from archive data.

Pure: takes already-fetched data, does no IO. The provider is responsible
for fetching ``std`` and ``qual`` (see ``last_processed_time``).
"""

import pandas as pd

def resume_point(std: pd.DataFrame, qual: pd.Series) -> pd.Timestamp | None:
    """Return the time from which new processing should resume.

    Processing has been done up to the later of:

    * the last standard data point that has a quality value
      (points with no quality were copied to the archive without being
      processed, so they don't count), and
    * the last entry in the quality series, whatever its code. This is what
      picks up a QC 100 checkpoint written after a deleted trailing chunk.

    Parameters
    ----------
    std : DataFrame
        Standard series fetched with quality shown. Indexed by timestamp,
        with a ``Quality`` column (NaN where a point has no quality).
    qual : Series
        The quality series, indexed by timestamp.

    Returns
    -------
    pd.Timestamp or None
        None if nothing has ever been processed.
    """
    candidates = []

    if not std.empty:
        # Quality code 0 means unknown/unprocessed; NaN means no value at all.
        # Neither counts as processed.
        # See QUALITY_CODES.rst for more information.
        has_quality = std["Quality"].fillna(0) > 0
        with_quality = std.index[has_quality]
        if len(with_quality):
            candidates.append(with_quality.max())

    if not qual.empty:
        candidates.append(qual.index.max())

    return max(candidates) if candidates else None
