"""Tests for the optional runtime registry."""

from __future__ import annotations

import types

from typing import Any
from unittest.mock import MagicMock

import pytest

from agentic_fabric.runners import registry
from agentic_fabric.runners.registry import RuntimeSpec, RuntimeUnavailableError


class FakeRunner:
    """Runner class loaded through the registry in tests."""


def install_fake_registry(monkeypatch: pytest.MonkeyPatch, spec: RuntimeSpec) -> None:
    """Replace the global runtime registry for one test."""
    monkeypatch.setattr(registry, "_RUNTIME_SPECS", {spec.name: spec})
    monkeypatch.setattr(registry, "_AVAILABILITY_CACHE", {})


def test_runtime_spec_serializes_metadata() -> None:
    spec = RuntimeSpec(
        name="fake",
        import_name="fake_runtime",
        runner_module="fake_runner",
        runner_class="FakeRunner",
        install="install fake",
        extra="fake",
        description="Fake runtime.",
    )

    assert spec.as_dict(available=True) == {
        "name": "fake",
        "import_name": "fake_runtime",
        "runner": "fake_runner:FakeRunner",
        "install": "install fake",
        "extra": "fake",
        "available": True,
        "description": "Fake runtime.",
    }


def test_register_runtime_replaces_spec_and_clears_cache(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(registry, "_RUNTIME_SPECS", {})
    monkeypatch.setattr(registry, "_AVAILABILITY_CACHE", {"fake": True})
    spec = RuntimeSpec("fake", "fake_runtime", "fake_runner", "FakeRunner", "install fake", "fake")

    registry.register_runtime(spec)

    assert registry.runtime_names() == ["fake"]
    assert registry.runtime_specs()["fake"] is spec
    assert "fake" not in registry._AVAILABILITY_CACHE

    with pytest.raises(TypeError):
        registry.runtime_specs()["other"] = spec  # type: ignore[index]


def test_unknown_runtime_reports_options(monkeypatch: pytest.MonkeyPatch) -> None:
    spec = RuntimeSpec("known", "known_runtime", "known_runner", "KnownRunner", "install known", "known")
    install_fake_registry(monkeypatch, spec)

    with pytest.raises(ValueError, match=r"Unknown runtime: missing. Options: \[known\]"):
        registry.get_runtime_spec("missing")


def test_runtime_availability_caches_import_success_and_unknown(monkeypatch: pytest.MonkeyPatch) -> None:
    spec = RuntimeSpec("fake", "fake_runtime", "fake_runner", "FakeRunner", "install fake", "fake")
    install_fake_registry(monkeypatch, spec)
    mock_import = MagicMock(return_value=types.ModuleType("fake_runtime"))
    monkeypatch.setattr(registry.importlib, "import_module", mock_import)

    assert registry.is_runtime_available("unknown") is False
    assert registry.is_runtime_available("fake") is True
    assert registry.is_runtime_available("fake") is True
    mock_import.assert_called_once_with("fake_runtime")
    assert registry.available_runtimes() == ["fake"]


def test_runtime_info_and_require_runtime_report_unavailable(monkeypatch: pytest.MonkeyPatch) -> None:
    spec = RuntimeSpec("fake", "missing_runtime", "fake_runner", "FakeRunner", "install fake", "fake")
    install_fake_registry(monkeypatch, spec)
    monkeypatch.setattr(registry.importlib, "import_module", MagicMock(side_effect=ImportError("missing")))

    assert registry.runtime_info("fake")["available"] is False
    assert registry.runtime_info() == [spec.as_dict(available=False)]

    with pytest.raises(RuntimeUnavailableError) as exc_info:
        registry.require_runtime("fake")

    assert exc_info.value.runtime == "fake"
    assert exc_info.value.install == "install fake"


def test_load_runner_imports_runner_class(monkeypatch: pytest.MonkeyPatch) -> None:
    spec = RuntimeSpec("fake", "fake_runtime", "fake_runner", "FakeRunner", "install fake", "fake")
    install_fake_registry(monkeypatch, spec)
    fake_runner_module = types.ModuleType("fake_runner")
    fake_runner_module.FakeRunner = FakeRunner

    def fake_import_module(name: str) -> Any:
        if name == "fake_runtime":
            return types.ModuleType("fake_runtime")
        if name == "fake_runner":
            return fake_runner_module
        raise ImportError(name)

    monkeypatch.setattr(registry.importlib, "import_module", fake_import_module)

    assert isinstance(registry.load_runner("fake"), FakeRunner)
    assert registry.install_command("fake") == "install fake"
