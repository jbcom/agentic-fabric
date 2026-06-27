"""Tests for utility file helpers."""

from __future__ import annotations

from pathlib import Path

from agentic_fabric.utils.files import load_config


def test_load_config_reads_utf8_yaml(tmp_path: Path) -> None:
    """YAML files should be decoded as UTF-8 across platforms."""
    config_file = tmp_path / "config.yaml"
    config_file.write_text("description: café\n", encoding="utf-8")

    assert load_config(config_file) == {"description": "café"}
