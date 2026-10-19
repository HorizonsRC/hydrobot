"""Resolve a batch entry into complete, ready-to-process run configs.

Resolving has two stages:

1.  EXPAND (see ``expansion.py``): one batch entry becomes one run config per
    layer. Pure; needs nothing but the entry.
2.  FILL (this module): complete the blanks in each run config, i.e.
    ``to_date`` (defaults to now) and ``from_date`` (where the last run got
    to, which means asking the provider).

The result is the run config: everything one processing run needs, and the
thing that gets saved for audit and for reprocessing.

Nothing here reads or writes files. The caller supplies the provider and the
current time, so everything is testable without a server or a clock.
"""

import copy
from datetime import datetime
from typing import Protocol, runtime_checkable

from hydrobot.orchestration.expansion import RunConfig, expand_layers
from hydrobot.providers.types import SiteInfo
from hydrobot.providers.protocol import DataProvider

# How dates are written in run configs: hyman-readable, to the minute
DATE_FORMAT = "%Y-%m-%d %H:%M"


@runtime_checkable
class ResolveProvider(Protocol):
    """What resolving needs from a provider (and nothing more).

    Resolving asks two questions: "where did processing last get to?" and
    "what is this site's code?". Asking for the whole DataProvider would make
    this module depend on methods it never calls (get_standard, ...), and
    would force every test fake to stub them all. Any full DataProvider
    satisfies this automatically, because it has both methods; so does a tiny
    test fake.
    """

    def last_processed_time(self, site: str, measurement: str) -> datetime | None:
        """When processing should resume, or None if never archived. """
        ...

    def get_site_info(self, site: str) -> SiteInfo:
        """Information about a site, including its short code."""
        ...

def fill_run_config(
    run: RunConfig,
    provider: ResolveProvider,
    *,
    now: datetime
) -> RunConfig:
    """Return a copy of ``run`` with ``to_date`` and ``from_date`` filled in.

    *   ``to_date``:    if missing (or None), set to ``now``.
    *   ``from_date``:  if missing (or None), set to the time the provider says
        processing last got to. The archive's measurement name is used for that
        lookup if the run has an ``archive_standard_measurement_name``,
        otherwise the normal ``standard_measurement_name``.

    Values already present are never overwritten, so a run config that a
    user has edited keeps their changes. The provider is only asked a
    question when ``from_date`` is actually missing.

    Parameters
    ----------
    run : dict
        The run config. Not modified.
    providers : DataProvider
        Used to look up where processing last got to.
    now : datetime
        The current time. Passed in (rather than read here) so that tests
        and reprocessing can control it.

    Returns
    -------
    dict
        A new, filled run config.

    Raises
    ------
    ValueError
        If ``from_date`` is missing and the archive has no processed data to
        infer it from. This is deliberately an error, not "process
        everything": an empty archive can mean a new site OR a wrong archive
        name (the server just returns nothing), and wrongly reprocessing a
        whole history costs far more than adding one config line.
    DataProviderError
        If the provider itself fails (bad config, server problem). Not caught
        here: deciding whether one failure stops a whole batch is the
        orchestrator's job.
    """
    filled = copy.deepcopy(run)

    if filled.get("site_code") is None:
        filled["site_code"] = provider.get_site_info(filled["site"]).code

    if filled.get("to_date") is None:
        filled["to_date"] = now.strftime(DATE_FORMAT)

    if filled.get("from_date") is None:
        site = filled["site"]
        measurement = _archive_measurement_name(filled)
        resume = provider.last_processed_time(site, measurement)
        if resume is None:
            raise ValueError(
                f"No from_date given for {site!r} / {measurement!r}, and the "
                "archive has no processed data to infer one from. If this is "
                "a new site, set from_date explicitly. If it is NOT new, the "
                "archive lookup is probably misconfigured: check "
                "archive_base_rul, archive_standard_hts_filename and "
                "archive_standard_measurement_name."
            )
        filled["from_date"] = resume.strftime(DATE_FORMAT)

    return filled

def resolve(
    entry: RunConfig,
    provider: ResolveProvider,
    *,
    now: datetime
) -> list[RunConfig]:
    """Expand a batch entry into run configs, then fill each one.

    Expansion happens first, so each run is filled using its own layer's
    measurement names (each layer gets its own archive lookup).
    """
    return [fill_run_config(run, provider, now=now) for run in expand_layers(entry)]


def _archive_measurement_name(run: RunConfig) -> str:
    """The measurement name to look up in the archive.

    The archive sometimes names a measurement differently from the live
    source. If the run says so (``archive_standard_measurement_name``), use
    that; otherwise the archive is assumed to use the normal name.
    """
    archive_name = run.get("archive_standard_measurement_name")
    return archive_name if archive_name is not None else run["standard_measurement_name"]

