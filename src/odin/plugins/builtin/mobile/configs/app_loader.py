"""App mapping configuration loader."""

from pathlib import Path

import yaml  # type: ignore[import-untyped]
from pydantic import BaseModel


class AndroidAppConfig(BaseModel):
    """Android app configuration."""

    package: str
    activity: str | None = None
    aliases: list[str] = []


class HarmonyAppConfig(BaseModel):
    """Harmony OS app configuration."""

    bundle: str
    module: str = "entry"
    ability: str = "MainAbility"
    aliases: list[str] = []


class IOSAppConfig(BaseModel):
    """iOS app configuration."""

    bundle_id: str
    aliases: list[str] = []


AppConfig = AndroidAppConfig | HarmonyAppConfig | IOSAppConfig


class AppMapper:
    """Maps app names/aliases to platform-specific configurations."""

    def __init__(self, config_path: Path | None = None):
        """Initialize with optional custom config path."""
        if config_path is None:
            config_path = Path(__file__).parent / "app_map.yaml"

        self._config_path = config_path
        self._android_apps: dict[str, AndroidAppConfig] = {}
        self._harmony_apps: dict[str, HarmonyAppConfig] = {}
        self._ios_apps: dict[str, IOSAppConfig] = {}
        # alias -> list of (platform, app_name) tuples
        self._alias_map: dict[str, list[tuple[str, str]]] = {}

        self._load_config()

    def _load_config(self) -> None:
        """Load and parse the app mapping configuration."""
        if not self._config_path.exists():
            return

        with self._config_path.open() as f:
            data = yaml.safe_load(f) or {}

        # Load Android apps
        for name, config in data.get("android", {}).items():
            android_config = AndroidAppConfig(**config)
            self._android_apps[name] = android_config
            self._register_aliases("android", name, android_config.aliases)

        # Load Harmony apps
        for name, config in data.get("harmony", {}).items():
            harmony_config = HarmonyAppConfig(**config)
            self._harmony_apps[name] = harmony_config
            self._register_aliases("harmony", name, harmony_config.aliases)

        # Load iOS apps
        for name, config in data.get("ios", {}).items():
            ios_config = IOSAppConfig(**config)
            self._ios_apps[name] = ios_config
            self._register_aliases("ios", name, ios_config.aliases)

    def _register_aliases(self, platform: str, app_name: str, aliases: list[str]) -> None:
        """Register aliases for an app."""
        # Register the app name itself
        key = app_name.lower()
        if key not in self._alias_map:
            self._alias_map[key] = []
        self._alias_map[key].append((platform, app_name))

        # Register all aliases
        for alias in aliases:
            key = alias.lower()
            if key not in self._alias_map:
                self._alias_map[key] = []
            self._alias_map[key].append((platform, app_name))

    def resolve(self, name: str, platform: str | None = None) -> tuple[str, AppConfig] | None:
        """Resolve app name or alias to configuration.

        Args:
            name: App name or alias
            platform: Optional platform filter (android/harmony/ios)

        Returns:
            Tuple of (platform, config) or None if not found
        """
        lookup = name.lower()

        if lookup in self._alias_map:
            entries = self._alias_map[lookup]

            # If platform filter is specified, find matching platform
            if platform:
                for resolved_platform, app_name in entries:
                    if resolved_platform == platform:
                        if resolved_platform == "android":
                            return ("android", self._android_apps[app_name])
                        elif resolved_platform == "harmony":
                            return ("harmony", self._harmony_apps[app_name])
                        elif resolved_platform == "ios":
                            return ("ios", self._ios_apps[app_name])
                return None

            # No platform filter - return first match
            resolved_platform, app_name = entries[0]
            if resolved_platform == "android":
                return ("android", self._android_apps[app_name])
            elif resolved_platform == "harmony":
                return ("harmony", self._harmony_apps[app_name])
            elif resolved_platform == "ios":
                return ("ios", self._ios_apps[app_name])

        return None

    def get_android_app(self, name: str) -> AndroidAppConfig | None:
        """Get Android app config by name or alias."""
        result = self.resolve(name, platform="android")
        if result and result[0] == "android":
            config = result[1]
            if isinstance(config, AndroidAppConfig):
                return config
        return None

    def get_harmony_app(self, name: str) -> HarmonyAppConfig | None:
        """Get Harmony OS app config by name or alias."""
        result = self.resolve(name, platform="harmony")
        if result and result[0] == "harmony":
            config = result[1]
            if isinstance(config, HarmonyAppConfig):
                return config
        return None

    def get_ios_app(self, name: str) -> IOSAppConfig | None:
        """Get iOS app config by name or alias."""
        result = self.resolve(name, platform="ios")
        if result and result[0] == "ios":
            config = result[1]
            if isinstance(config, IOSAppConfig):
                return config
        return None

    def list_apps(self, platform: str | None = None) -> dict[str, list[str]]:
        """List all registered apps by platform.

        Args:
            platform: Optional platform filter

        Returns:
            Dict mapping platform to list of app names
        """
        result: dict[str, list[str]] = {}

        if platform is None or platform == "android":
            result["android"] = list(self._android_apps.keys())

        if platform is None or platform == "harmony":
            result["harmony"] = list(self._harmony_apps.keys())

        if platform is None or platform == "ios":
            result["ios"] = list(self._ios_apps.keys())

        return result


# Global singleton instance
_app_mapper: AppMapper | None = None


def get_app_mapper() -> AppMapper:
    """Get the global AppMapper instance."""
    global _app_mapper
    if _app_mapper is None:
        _app_mapper = AppMapper()
    return _app_mapper
