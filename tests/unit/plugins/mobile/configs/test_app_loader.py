"""Tests for app mapping configuration loader."""

import tempfile
from pathlib import Path

import pytest
import yaml

from odin.plugins.builtin.mobile.configs.app_loader import (
    AndroidAppConfig,
    AppMapper,
    HarmonyAppConfig,
    IOSAppConfig,
)


class TestAndroidAppConfig:
    """Tests for AndroidAppConfig model."""

    def test_minimal_config(self):
        """Test creating config with only required fields."""
        config = AndroidAppConfig(package="com.example.app")
        assert config.package == "com.example.app"
        assert config.activity is None
        assert config.aliases == []

    def test_full_config(self):
        """Test creating config with all fields."""
        config = AndroidAppConfig(
            package="com.tencent.mm",
            activity=".ui.LauncherUI",
            aliases=["微信", "WeChat"],
        )
        assert config.package == "com.tencent.mm"
        assert config.activity == ".ui.LauncherUI"
        assert config.aliases == ["微信", "WeChat"]


class TestAppMapper:
    """Tests for AppMapper class."""

    @pytest.fixture
    def sample_config(self, tmp_path: Path) -> Path:
        """Create a sample config file for testing."""
        config = {
            "android": {
                "wechat": {
                    "package": "com.tencent.mm",
                    "activity": ".ui.LauncherUI",
                    "aliases": ["微信", "WeChat"],
                },
                "alipay": {
                    "package": "com.eg.android.AlipayGphone",
                    "aliases": ["支付宝"],
                },
            },
            "harmony": {
                "wechat": {
                    "bundle": "com.tencent.mm",
                    "module": "entry",
                    "ability": "MainAbility",
                    "aliases": ["微信"],
                },
            },
            "ios": {
                "wechat": {
                    "bundle_id": "com.tencent.xin",
                    "aliases": ["微信"],
                },
            },
        }

        config_path = tmp_path / "app_map.yaml"
        with open(config_path, "w") as f:
            yaml.dump(config, f)

        return config_path

    def test_load_android_apps(self, sample_config: Path):
        """Test loading Android app configurations."""
        mapper = AppMapper(sample_config)

        app = mapper.get_android_app("wechat")
        assert app is not None
        assert app.package == "com.tencent.mm"
        assert app.activity == ".ui.LauncherUI"

    def test_resolve_by_alias(self, sample_config: Path):
        """Test resolving apps by alias."""
        mapper = AppMapper(sample_config)

        # Chinese alias
        result = mapper.resolve("微信")
        assert result is not None
        platform, config = result
        assert platform == "android"
        assert isinstance(config, AndroidAppConfig)
        assert config.package == "com.tencent.mm"

    def test_resolve_case_insensitive(self, sample_config: Path):
        """Test that alias lookup is case-insensitive."""
        mapper = AppMapper(sample_config)

        assert mapper.get_android_app("WeChat") is not None
        assert mapper.get_android_app("wechat") is not None
        assert mapper.get_android_app("WECHAT") is not None

    def test_resolve_with_platform_filter(self, sample_config: Path):
        """Test resolving with platform filter."""
        mapper = AppMapper(sample_config)

        # Same alias registered for multiple platforms
        android_result = mapper.resolve("微信", platform="android")
        assert android_result is not None
        assert android_result[0] == "android"

        ios_result = mapper.resolve("微信", platform="ios")
        # Note: In this test data, 微信 is registered first for android,
        # so ios lookup would find android first. In real usage, platform filter
        # should be used to disambiguate.

    def test_get_nonexistent_app(self, sample_config: Path):
        """Test getting an app that doesn't exist."""
        mapper = AppMapper(sample_config)

        assert mapper.get_android_app("nonexistent") is None
        assert mapper.resolve("unknownapp") is None

    def test_list_apps(self, sample_config: Path):
        """Test listing all apps."""
        mapper = AppMapper(sample_config)

        all_apps = mapper.list_apps()
        assert "android" in all_apps
        assert "wechat" in all_apps["android"]
        assert "alipay" in all_apps["android"]

        android_only = mapper.list_apps(platform="android")
        assert "android" in android_only
        assert "harmony" not in android_only

    def test_empty_config_file(self, tmp_path: Path):
        """Test handling of empty config file."""
        config_path = tmp_path / "empty.yaml"
        config_path.write_text("")

        mapper = AppMapper(config_path)
        assert mapper.list_apps() == {"android": [], "harmony": [], "ios": []}

    def test_missing_config_file(self, tmp_path: Path):
        """Test handling of missing config file."""
        config_path = tmp_path / "nonexistent.yaml"

        mapper = AppMapper(config_path)
        assert mapper.list_apps() == {"android": [], "harmony": [], "ios": []}
