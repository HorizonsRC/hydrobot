"""Smoke test: run every provider read against the REAL server, once.

Our unit tests use fake clients, so nothing in them proves that the keyword
arguments the provider hands to whurl (datetimes, ts_type values,
show_quality...) are what your whurl actually accepts. This does.

    python scripts/try_provider_live.py CONFIG.yaml "Site Name" "Measurement Name" \
        [--check "Check Measurement Name"]

CONFIG.yaml is any hydrobot config that has a ``provider_params:`` block.
Each read is run on its own, so one failure doesn't hide the others. For every
read it prints the request URL it used: paste it into a browser to see exactly
what the server sends back.
"""

import argparse
from datetime import datetime, timedelta

import yaml

from hydrobot.providers.horizons import HorizonsProvider, HorizonsProviderConfig
from hydrobot.providers.types import SiteInfo


def show(label, read, rows=0):
    """Run one read; print what came back, or what went wrong.

    ``rows`` > 0 also prints that many rows from each end of the data, so the
    VALUES can be eyeballed (are the data sensible? are the numvers plausible?),
    not just the column types.
    """
    print(f"\n=== {label}")
    try:
        result = read()
    except Exception as e:  # deliberately broad: we want to SEE every failure
        print(f"FAILED  {type(e).__name__}: {e}")
        return
    if isinstance(result, SiteInfo):
        # The full metadata is dozens of fields; just show the point of the test.
        print(f"code: {result.code}   ({len(result.metadata)} other fields returned)")
    elif hasattr(result, "data"):
        print(f"rows: {len(result.data)}")
        # Column TYPES matter: "Quality" arriving as text once broke resume_point.
        print(f"columns: { {c: str(t) for c, t in result.data.dtypes.items()} }")
        if len(result.data):
            index = result.data.index
            print(f"index: {index.dtype}    {index.min()}   to  {index.max()}")
            if rows:
                print(result.data.head(rows).to_string())
                if len(result.data) > rows:
                    print("    ...")
                    print(result.data.tail(rows).to_string(header=False))
        origin = result.metadata.get("origin", {})
        print(f"request_url: {origin.get('request_url')}")
    else:
        print(f"result: {result!r}")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("config")
    ap.add_argument("site")
    ap.add_argument("measurement")
    ap.add_argument("--check", help="check measurement name (optional)")
    ap.add_argument("--days", type=int, default=3, help="how far back to read")
    ap.add_argument("--show", type=int, default=0, metavar="N",
                    help="also print N rows from each end of every result")
    args = ap.parse_args()

    with open(args.config) as f:
        params = yaml.safe_load(f)["provider_params"]
    to_date = datetime.now()
    from_date = to_date - timedelta(days=args.days)
    site, measurement = args.site, args.measurement

    # The provider keeps its connections open between reads and closes them
    # when this block ends. Every read below reuses the same connections, which
    # is also a check that one read doesn't break the next.
    with HorizonsProvider(HorizonsProviderConfig(**params)) as provider:
        show("get_site_info", lambda: provider.get_site_info(site))
        show("get_standard", lambda: provider.get_standard(site, measurement, from_date, to_date), args.show)
        show("get_quality", lambda: provider.get_quality(site, measurement, from_date, to_date), args.show)
        if args.check:
            show("get_check", lambda: provider.get_check(site, args.check, from_date, to_date), args.show)
        show("last_processed_time", lambda: provider.last_processed_time(site, measurement))


if __name__ == "__main__":
    main()
