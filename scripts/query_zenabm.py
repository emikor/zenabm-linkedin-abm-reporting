#!/usr/bin/env python3
"""
query_zenabm.py — CLI wrapper for the ZenABM API client

Usage:
  python query_zenabm.py <function_name> '<json_args>'

Examples:
  python query_zenabm.py get_overview '{"start":"2024-04-01","end":"2024-04-07"}'
  python query_zenabm.py get_deals '{"start":"2024-04-01","end":"2024-04-30"}'
  python query_zenabm.py get_format_summary '{"start":"2024-04-01","end":"2024-04-07"}'
  python query_zenabm.py get_abm_stages '{}'
  python query_zenabm.py get_impression_hogs '{"start":"2024-04-01","end":"2024-04-07","threshold_multiplier":5}'

All output is printed as pretty-printed JSON to stdout.
Errors (API failures, missing token) are printed to stderr and exit with code 1.
"""

import json
import sys
from pathlib import Path

# Allow running this script from any directory
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lib.zenabm import ZenABMClient, detect_format


# ---------------------------------------------------------------------------
# Function registry — maps CLI name to (client_method, arg_mapping)
# ---------------------------------------------------------------------------
# Each entry is a tuple of:
#   (method_name_on_client, [list_of_kwarg_names_in_order])
# The JSON args dict is unpacked as keyword arguments.

FUNCTION_REGISTRY: dict[str, str] = {
    # Headline metrics
    "get_overview": "get_overview",
    "get_wow_metrics": "get_wow_metrics",
    # Campaign groups
    "get_campaign_groups": "get_campaign_groups",
    "get_campaign_group_weekly": "get_campaign_group_weekly",
    # Ad sets / campaigns
    "get_ad_sets": "get_ad_sets",
    "get_ad_set_weekly": "get_ad_set_weekly",
    "get_format_summary": "get_format_summary",
    # Companies
    "get_companies": "get_companies",
    "get_impression_hogs": "get_impression_hogs",
    # Deals
    "get_deals": "get_deals",
    # ABM stages
    "get_abm_stages": "get_abm_stages",
    "get_companies_entering_stage": "get_companies_entering_stage",
    "get_stage_history": "get_stage_history",
    # Spend / personas
    "get_ad_spend": "get_ad_spend",
    "get_job_titles": "get_job_titles",
    # Misc
    "get_abm_campaigns": "get_abm_campaigns",
    "get_intents": "get_intents",
}

# Functions that take no client instance (pure helpers)
PURE_FUNCTIONS = {
    "detect_format": detect_format,
}


def main():
    if len(sys.argv) < 2:
        print(__doc__, file=sys.stderr)
        sys.exit(1)

    func_name = sys.argv[1]

    # Parse optional JSON args
    raw_args = sys.argv[2] if len(sys.argv) > 2 else "{}"
    try:
        kwargs = json.loads(raw_args)
    except json.JSONDecodeError as exc:
        print(f"[ERROR] Invalid JSON arguments: {exc}", file=sys.stderr)
        print(f"  Received: {raw_args!r}", file=sys.stderr)
        sys.exit(1)

    # Pure (non-client) functions
    if func_name in PURE_FUNCTIONS:
        try:
            result = PURE_FUNCTIONS[func_name](**kwargs)
            print(json.dumps(result, indent=2, default=str))
            return
        except Exception as exc:
            print(f"[ERROR] {func_name} failed: {exc}", file=sys.stderr)
            sys.exit(1)

    # Client functions
    if func_name not in FUNCTION_REGISTRY:
        available = sorted(list(FUNCTION_REGISTRY.keys()) + list(PURE_FUNCTIONS.keys()))
        print(f"[ERROR] Unknown function: {func_name!r}", file=sys.stderr)
        print(f"\nAvailable functions:", file=sys.stderr)
        for name in available:
            print(f"  {name}", file=sys.stderr)
        sys.exit(1)

    method_name = FUNCTION_REGISTRY[func_name]

    try:
        client = ZenABMClient()
        method = getattr(client, method_name)
        result = method(**kwargs)
        print(json.dumps(result, indent=2, default=str))
    except SystemExit:
        # setup_check() already printed a helpful message
        raise
    except Exception as exc:
        import traceback
        print(f"[ERROR] {func_name} failed: {exc}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
