"""Settings management for EBI application.

Handles loading/saving persistent OAuth and authentication settings.
Stores configuration in a local JSON file at %APPDATA%\EBI\settings.json
"""

import json
import os
from pathlib import Path
from typing import Dict, Optional


class SettingsManager:
    """Manages persistent application settings."""

    def __init__(self, config_dir: Optional[str] = None):
        """Initialize settings manager.

        Args:
            config_dir: Directory to store config file. Defaults to %APPDATA%/EBI
        """
        if config_dir is None:
            # Use standard Windows app data directory
            if os.name == "nt":
                config_dir = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "EBI")
            else:
                config_dir = os.path.expanduser("~/.config/ebi")

        self.config_dir = Path(config_dir)
        self.config_file = self.config_dir / "settings.json"
        self._settings = self._load_settings()

    def _load_settings(self) -> Dict:
        """Load settings from config file."""
        if self.config_file.exists():
            try:
                with open(self.config_file, "r") as f:
                    return json.load(f)
            except Exception:
                return self._default_settings()
        return self._default_settings()

    def _default_settings(self) -> Dict:
        """Return default settings."""
        return {
            "institution_url": "",
            "oauth_client_id": "",
            "oauth_redirect_uri": "default",
            "rest_access_token": "",
            "rest_admin_token": "",
            "debug": False,
        }

    def save(self):
        """Save settings to config file."""
        self.config_dir.mkdir(parents=True, exist_ok=True)
        with open(self.config_file, "w") as f:
            json.dump(self._settings, f, indent=2)

    def get(self, key: str, default=None):
        """Get a setting value."""
        return self._settings.get(key, default)

    def set(self, key: str, value):
        """Set a setting value."""
        self._settings[key] = value

    def get_all(self) -> Dict:
        """Get all settings."""
        return self._settings.copy()

    def is_configured(self) -> bool:
        """Check if settings are configured."""
        return bool(self.get("institution_url"))

    def has_credentials(self) -> bool:
        """Check if any authentication credentials are configured."""
        return bool(
            self.get("oauth_client_id")
            or self.get("rest_access_token")
            or self.get("rest_admin_token")
        )
