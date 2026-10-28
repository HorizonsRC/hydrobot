"""Smoke test: run every whurl-based provider read against the REAL server.

Our unit tests use fake clients, so nothing in them proves that the keyword
arguments the provider hands to whurl (datetimes, ts_type values,
show_quality...) are what whurl actually accepts. Whurl has an extensive
integration test suite (tests that hit real servers), but this script
provides an easy way to test how hydrobot really interacts with whurl.

Usage:

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


def show(label, read):
    """Make one call, print what came back, or what went wrong."""
    print(f"\n=== {label}")
    try:
        result=read()
    except Exception as e:  # deliberately broad: we want to SEE every failure
        print(f"FAILED   {type(e).__name__}: {e}")
        return
    if hasattr(result, "data"):
        print(f"rows: {len(result.data)}  columns: {list(result.data.columns)}")
        origin = result.metadata.get("origin", {})
        print(f"request_url: {origin.get('request_url')}")
    else:
        print(f"result: {result!r}")


def main():
    # Using the docstring of this file as a usage doc
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("config")
    ap.add_argument("site")
    ap.add_argument("measurement")
    ap.add_argument("--check", help="check measurement name (optional)")
    ap.add_argument("--days", type=int, default=3, help="how far back to read")
    args = ap.parse_args()

    with open(args.config) as f:
        params = yaml.safe_load(f)["provider_params"]
    provider = HorizonsProvider(HorizonsProviderConfig(**params))

    to_date = datetime.now()
    from_date = to_date - timedelta(days=args.days)
    site, measurement = args.site, args.measurement

    show("get_site_info", lambda: provider.get_site_info(site))
    show("get_standard", lambda: provider.get_standard(site, measurement, from_date, to_date))
    show("get_quality", lambda: provider.get_quality(site, measurement, from_date, to_date))
    if args.check:
        show("get_check", lambda: provider.get_check(site, args.check, from_date, to_date))
    show("last_processed_time", lambda: provider.last_processed_time(site, measurement))


if __name__ == "__main__":
    main()


