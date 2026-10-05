"""Test hydrobot.config.settings."""

from pathlib import Path

import pytest

from hydrobot.config import settings


class TestDataDir:
    """Test settings.data_dir."""

    def test_defaults_to_bundled_config_directory(self, monkeypatch):
        """With no override set, data_dir() is hydrobot/config/ itself."""
        monkeypatch.delenv("HYDROBOT_DATA_DIR", raising=False)

        result = settings.data_dir()

        assert settings.__file__ is not None
        assert result == Path(settings.__file__).resolve().parent
        # Sanity check: this is actually the real, existing directory,
        # not just a path that happens to match by construction.
        assert result.is_dir()
        assert (result / "settings.py").is_file()

    def test_uses_override_when_set(self, monkeypatch, tmp_path):
        """HYDROBOT_DATA_DIR, when set, is returned as a Path."""
        monkeypatch.setenv("HYDROBOT_DATA_DIR", str(tmp_path))

        assert settings.data_dir() == tmp_path

    def test_override_need_not_exist(self, monkeypatch, tmp_path):
        """data_dir() doesn't require the override to already exist.

        Validating existence is the caller's job (e.g. when it tries to
        actually read a file from there), not this function's.
        """
        missing = tmp_path / "does-not-exist-yet"
        monkeypatch.setenv("HYDROBOT_DATA_DIR", str(missing))

        assert settings.data_dir() == missing


class TestHorizonsSqlHost:
    """Test settings.horizons_sql_host."""

    def test_returns_configured_value(self, monkeypatch):
        monkeypatch.setenv("HYDROBOT_HORIZONS_SQL_HOST", "sql.example.com")

        assert settings.horizons_sql_host() == "sql.example.com"

    def test_raises_when_unset(self, monkeypatch):
        monkeypatch.delenv("HYDROBOT_HORIZONS_SQL_HOST", raising=False)

        with pytest.raises(settings.MissingSettingError) as exc_info:
            settings.horizons_sql_host()

        assert "HYDROBOT_HORIZONS_SQL_HOST" in str(exc_info.value)

    def test_raises_when_set_to_empty_string(self, monkeypatch):
        """An empty string is treated the same as unset, not a valid host."""
        monkeypatch.setenv("HYDROBOT_HORIZONS_SQL_HOST", "")

        with pytest.raises(settings.MissingSettingError):
            settings.horizons_sql_host()

class TestHorizonsDatabaseNames:
    """Test settings.horizons_survey123_db and settings.horizons_hilltop_db."""

    def test_survey123_db_default(self, monkeypatch):
        monkeypatch.delenv("HYDROBOT_HORIZONS_SURVEY123_DB", raising=False)

        assert settings.horizons_survey123_db() == "survey123"

    def test_survey123_db_override(self, monkeypatch):
        monkeypatch.setenv("HYDROBOT_HORIZONS_SURVEY123_DB", "survey123_test")

        assert settings.horizons_survey123_db() == "survey123_test"

    def test_hilltop_db_default(self, monkeypatch):
        monkeypatch.delenv("HYDROBOT_HORIZONS_HILLTOP_DB", raising=False)

        assert settings.horizons_hilltop_db() == "hilltop"

    def test_hilltop_db_override(self, monkeypatch):
        monkeypatch.setenv("HYDROBOT_HORIZONS_HILLTOP_DB", "hilltop_test")

        assert settings.horizons_hilltop_db() == "hilltop_test"


class TestMissingSettingError:
    """Test the MissingSettingError exception itself."""

    def test_is_a_runtime_error(self):
        """Callers that only catch broad errors still catch this."""
        assert issubclass(settings.MissingSettingError, RuntimeError)



