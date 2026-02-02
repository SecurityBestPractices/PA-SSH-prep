"""Tests for src/panos_upgrade.py"""

import pytest
from src.panos_upgrade import Version, get_upgrade_path, UPGRADE_PATHS


class TestVersion:
    """Tests for Version class."""

    def test_parse_standard_version(self):
        v = Version.parse("10.2.4")
        assert v.major == 10
        assert v.minor == 2
        assert v.patch == 4
        assert v.original == "10.2.4"

    def test_parse_hotfix_version(self):
        v = Version.parse("11.2.10-h2")
        assert v.major == 11
        assert v.minor == 2
        assert v.patch == 10
        assert v.original == "11.2.10-h2"

    def test_parse_with_whitespace(self):
        v = Version.parse("  10.1.0  ")
        assert v.major == 10
        assert v.minor == 1
        assert v.patch == 0

    def test_parse_invalid_version(self):
        with pytest.raises(ValueError):
            Version.parse("invalid")

        with pytest.raises(ValueError):
            Version.parse("10.2")

        with pytest.raises(ValueError):
            Version.parse("")

    def test_str_representation(self):
        v = Version.parse("10.2.4")
        assert str(v) == "10.2.4"

        v = Version.parse("11.2.10-h2")
        assert str(v) == "11.2.10"

    def test_major_minor(self):
        v = Version.parse("10.2.4")
        assert v.major_minor() == "10.2"

        v = Version.parse("11.1.0")
        assert v.major_minor() == "11.1"

    def test_base_version(self):
        v = Version.parse("10.2.4")
        assert v.base_version() == "10.2.0"

        v = Version.parse("11.2.10-h2")
        assert v.base_version() == "11.2.0"

    def test_comparison_less_than(self):
        v1 = Version.parse("10.1.0")
        v2 = Version.parse("10.2.0")
        assert v1 < v2

        v1 = Version.parse("10.2.3")
        v2 = Version.parse("10.2.4")
        assert v1 < v2

        v1 = Version.parse("9.1.14")
        v2 = Version.parse("10.0.0")
        assert v1 < v2

    def test_comparison_equal(self):
        v1 = Version.parse("10.2.4")
        v2 = Version.parse("10.2.4")
        assert v1 == v2

        v1 = Version.parse("10.2.4")
        v2 = Version.parse("10.2.4-h1")
        assert v1 == v2  # Hotfix suffix ignored for comparison

    def test_comparison_greater_than_or_equal(self):
        v1 = Version.parse("11.0.0")
        v2 = Version.parse("10.2.9")
        assert v1 >= v2

        v1 = Version.parse("10.2.4")
        v2 = Version.parse("10.2.4")
        assert v1 >= v2

    def test_comparison_with_non_version(self):
        """Test Version.__eq__ returns NotImplemented for non-Version objects."""
        v1 = Version.parse("10.2.4")
        result = v1.__eq__("10.2.4")
        assert result is NotImplemented

        result = v1.__eq__(10)
        assert result is NotImplemented

        result = v1.__eq__(None)
        assert result is NotImplemented


class TestGetUpgradePath:
    """Tests for get_upgrade_path function."""

    def test_no_upgrade_needed(self):
        # Already at target version
        path = get_upgrade_path("11.2.4", "11.2.4")
        assert path == []

        # Already past target version
        path = get_upgrade_path("11.2.5", "11.2.4")
        assert path == []

    def test_same_major_minor_upgrade(self):
        # Upgrade within same major.minor
        path = get_upgrade_path("10.2.0", "10.2.4")
        assert path == ["10.2.4"]

        path = get_upgrade_path("11.2.3", "11.2.10")
        assert path == ["11.2.10"]

    def test_single_major_version_jump(self):
        # 10.2.x -> 11.0.x
        path = get_upgrade_path("10.2.4", "11.0.3")
        assert "11.0.0" in path or "11.0.3" in path

    def test_multiple_major_version_jumps(self):
        # 10.1.x -> 11.2.x requires multiple steps
        path = get_upgrade_path("10.1.0", "11.2.4")
        assert len(path) >= 2  # At least 10.2.0 and then 11.x

    def test_upgrade_to_12x(self):
        # 11.2.x -> 12.1.x
        path = get_upgrade_path("11.2.4", "12.1.4")
        assert "12.1.2" in path or "12.1.4" in path

    def test_long_upgrade_path(self):
        # 9.1.x -> 11.2.x requires many steps
        path = get_upgrade_path("9.1.0", "11.2.4")
        assert len(path) >= 3  # Multiple major version jumps

    def test_upgrade_from_unknown_version(self):
        """Test upgrade from a version not in UPGRADE_PATHS goes directly to target."""
        # 8.1 is not in UPGRADE_PATHS, so should go directly to target if in same major.minor
        path = get_upgrade_path("8.1.0", "8.1.5")
        assert path == ["8.1.5"]


class TestUpgradePaths:
    """Tests for UPGRADE_PATHS constant."""

    def test_upgrade_paths_exist(self):
        assert "9.1" in UPGRADE_PATHS
        assert "10.1" in UPGRADE_PATHS
        assert "10.2" in UPGRADE_PATHS
        assert "11.0" in UPGRADE_PATHS
        assert "11.1" in UPGRADE_PATHS
        assert "11.2" in UPGRADE_PATHS

    def test_12_1_base_version(self):
        # 12.1 base version is 12.1.2, not 12.1.0
        assert UPGRADE_PATHS["11.2"] == "12.1.2"

    def test_upgrade_paths_are_valid_versions(self):
        for source, target in UPGRADE_PATHS.items():
            # Each target should be a valid version string
            v = Version.parse(target)
            assert v.major >= 9
            assert v.minor >= 0
            assert v.patch >= 0
