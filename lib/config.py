"""
config.py — Load ZenABM credentials from .env

Looks for .env in the plugin root directory (two levels up from this file).
Falls back to environment variables if .env is not present.
"""

import os
import sys
from pathlib import Path

# Resolve plugin root: lib/ is one level below plugin root
PLUGIN_ROOT = Path(__file__).resolve().parent.parent


def _load_dotenv():
    """Manually load .env from plugin root without requiring python-dotenv at import time."""
    env_path = PLUGIN_ROOT / ".env"
    if env_path.exists():
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, _, value = line.partition("=")
                key = key.strip()
                value = value.strip().strip('"').strip("'")
                # Only set if not already in environment (env vars take precedence)
                if key not in os.environ:
                    os.environ[key] = value


# Load .env on module import
_load_dotenv()


def get_config() -> dict:
    """Return a dict with ZENABM_API_TOKEN and ZENABM_BASE_URL."""
    token = os.environ.get("ZENABM_API_TOKEN", "").strip()
    base_url = os.environ.get("ZENABM_BASE_URL", "https://app.zenabm.com/api/v1").rstrip("/")
    return {
        "token": token,
        "base_url": base_url,
    }


def setup_check():
    """
    Verify that ZENABM_API_TOKEN is configured.
    Prints a friendly error and exits with code 1 if the token is missing.
    Call this at the top of any script that needs API access.
    """
    cfg = get_config()
    if not cfg["token"]:
        print(
            "\n[ERROR] ZENABM_API_TOKEN is not set.\n"
            "\nTo fix this, run the setup wizard:\n"
            f"  bash {PLUGIN_ROOT}/scripts/setup.sh\n"
            "\nOr set the token manually:\n"
            f"  echo 'ZENABM_API_TOKEN=your_token_here' > {PLUGIN_ROOT}/.env\n",
            file=sys.stderr,
        )
        sys.exit(1)
    return cfg
