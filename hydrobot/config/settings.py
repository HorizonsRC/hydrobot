"""Centralised environment-driven configuration for hydrobot.

Mirrors whurl's own convention (see whurl.client): configuration comes
from environment variables, optionally loaded from a local .env file via
python-dotenv. No hostnames, database names, or credentials are
hardcoded in source.

This module only owns *where configuration comes from*. It knows nothing
about SQLAlchemy, Hilltop, or any specific provider's connection
mechanics -- callers (e.g. hydrobot.config.horizons_source) are
responsible for using these values to actually connect to something.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


class MissingSettingError(RuntimeError):
    """Raised when a required environment variable is not set."""


def _require(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise MissingSettingError(
            f"Required environment variable '{name}' is not set. "
            "See CONFIGURATION.md for the full list of variables hydrobot needs."
        )
    return value


def data_dir() -> Path:
    """Root directory for deployment-supplied config overrides.

    Defaults to hydrobot's own bundled `hydrobot/config/` directory, so
    nothing changes for a deployment that hasn't set this. Set
    HYDROBOT_DATA_DIR to point at a directory of site overrides, policy
    YAML, or another provider's query templates, without forking the
    package.
    """
    value = os.getenv("HYDROBOT_DATA_DIR")
    if value:
        return Path(value)
    return Path(__file__).resolve().parent


# --- Horizons SQL provider settings -------------------------------------
# Specific to hydrobot.config.horizons_source, Horizons' Survey123/Hilltop
# SQL inspection-data provider. Namespaced "horizons_*" rather than
# treated as a generic "the SQL config" -- a different council's provider
# may not use SQL Server, or SQL, at all.


def horizons_sql_host() -> str:
    """Hostname of the Horizons SQL Server instance.

    Required, no default. Previously this was guessed from the OS
    (Windows vs. Linux), which hid a specific internal hostname in
    source and silently broke on any other platform.
    """
    return _require("HYDROBOT_HORIZONS_SQL_HOST")


def horizons_survey123_db() -> str:
    """Database name for the Survey123 inspection-data database."""
    return os.getenv("HYDROBOT_HORIZONS_SURVEY123_DB", "survey123")


def horizons_hilltop_db() -> str:
    """Database name for the Hilltop SQL database."""
    return os.getenv("HYDROBOT_HORIZONS_HILLTOP_DB", "hilltop")
