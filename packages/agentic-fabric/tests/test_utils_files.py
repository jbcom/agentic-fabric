"""Tests for utility file helpers."""

from __future__ import annotations

from pathlib import Path

import pytest

from agentic_fabric.utils.files import load_config


def test_load_config_reads_utf8_yaml(tmp_path: Path) -> None:
    """YAML files should be decoded as UTF-8 across platforms."""
    config_file = tmp_path / "config.yaml"
    config_file.write_text("description: café\n", encoding="utf-8")

    assert load_config(config_file) == {"description": "café"}


def test_load_config_rejects_non_mapping_yaml(tmp_path: Path) -> None:
    """Top-level YAML sequences should fail with a clear error."""
    config_file = tmp_path / "config.yaml"
    config_file.write_text("- one\n- two\n", encoding="utf-8")

    with pytest.raises(TypeError, match="Expected mapping"):
        load_config(config_file)
