"""Tests for framework auto-detection edge cases in the decomposer module."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from agentic_fabric.core.decomposer import (
    _framework_cache,
    _get_install_command,
    decompose_crew,
    detect_framework,
    get_available_frameworks,
    get_framework_info,
    get_runner,
    is_cli_runner_available,
    is_framework_available,
    run_crew_auto,
)
from agentic_fabric.runners.registry import clear_runtime_cache


class TestIsFrameworkAvailable:
    """Edge cases for is_framework_available."""

    def setup_method(self):
        """Clear the framework cache before each test."""
        _framework_cache.clear()
        clear_runtime_cache()

    def test_unsupported_framework_returns_false(self) -> None:
        """An unsupported framework name should return False immediately."""
        result = is_framework_available("pytorch")
        assert result is False

    def test_unsupported_framework_is_cached_as_false(self) -> None:
        """Unsupported framework names should still be cached."""
        is_framework_available("unsupported_thing")
        assert "unsupported_thing" in _framework_cache
        assert _framework_cache["unsupported_thing"] is False

    def test_import_failure_returns_false(self) -> None:
        """When importlib.import_module raises ImportError, return False."""
        with patch("agentic_fabric.core.decomposer.importlib.import_module", side_effect=ImportError("nope")):
            result = is_framework_available("crewai")
        assert result is False

    def test_successful_import_returns_true_and_caches(self) -> None:
        """A successful import should cache True."""
        with patch("agentic_fabric.core.decomposer.importlib.import_module"):
            result = is_framework_available("crewai")
        assert result is True
        assert _framework_cache["crewai"] is True

    def test_cache_hit_does_not_reimport(self) -> None:
        """Once cached, no re-import should occur."""
        _framework_cache["strands"] = True
        with patch("agentic_fabric.core.decomposer.importlib.import_module") as mock_import:
            result = is_framework_available("strands")
        assert result is True
        mock_import.assert_not_called()

    def test_empty_string_framework_returns_false(self) -> None:
        """Empty string framework name should return False."""
        result = is_framework_available("")
        assert result is False


class TestDetectFramework:
    """Edge cases for detect_framework."""

    def test_preferred_auto_falls_through_to_detection(self) -> None:
        """preferred='auto' should be treated as no preference."""

        def mock_available(framework):
            return framework == "strands"

        with patch(
            "agentic_fabric.core.decomposer.is_framework_available",
            side_effect=mock_available,
        ):
            result = detect_framework(preferred="auto")

        assert result == "strands"

    def test_preferred_unavailable_falls_back_gracefully(self) -> None:
        """When preferred framework is unavailable, fall back to auto-detect."""

        def mock_available(framework):
            return framework == "crewai"

        with patch(
            "agentic_fabric.core.decomposer.is_framework_available",
            side_effect=mock_available,
        ):
            result = detect_framework(preferred="strands")

        assert result == "crewai"

    def test_preferred_none_auto_detects(self) -> None:
        """preferred=None should auto-detect."""

        def mock_available(framework):
            return framework == "langgraph"

        with patch(
            "agentic_fabric.core.decomposer.is_framework_available",
            side_effect=mock_available,
        ):
            result = detect_framework(preferred=None)

        assert result == "langgraph"

    def test_crewai_has_highest_priority(self) -> None:
        """When all frameworks available, crewai should win."""
        with patch(
            "agentic_fabric.core.decomposer.is_framework_available",
            return_value=True,
        ):
            result = detect_framework()

        assert result == "crewai"

    def test_error_message_lists_install_options(self) -> None:
        """RuntimeError should include installation instructions."""
        with (
            patch("agentic_fabric.core.decomposer.is_framework_available", return_value=False),
            pytest.raises(RuntimeError, match="pip install crewai"),
        ):
            detect_framework()


class TestGetAvailableFrameworks:
    """Edge cases for get_available_frameworks."""

    def test_returns_only_available(self) -> None:
        """Should only include frameworks that are importable."""

        def mock_available(framework):
            return framework == "strands"

        with patch(
            "agentic_fabric.core.decomposer.is_framework_available",
            side_effect=mock_available,
        ):
            result = get_available_frameworks()

        assert result == ["strands"]

    def test_preserves_priority_order(self) -> None:
        """Returned list should preserve priority order."""

        def mock_available(framework):
            return framework in ["strands", "crewai"]

        with patch(
            "agentic_fabric.core.decomposer.is_framework_available",
            side_effect=mock_available,
        ):
            result = get_available_frameworks()

        assert result == ["crewai", "strands"]


class TestRunnerDispatch:
    """Tests for framework runner dispatch helpers."""

    def test_get_runner_auto_detects_and_instantiates_runner(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """get_runner should instantiate the registered runner class."""

        class FakeRunner:
            pass

        class FakeSpec:
            runner_module = "fake.runner"
            runner_class = "FakeRunner"

        fake_module = type("FakeModule", (), {"FakeRunner": FakeRunner})
        monkeypatch.setattr("agentic_fabric.core.decomposer.detect_framework", lambda: "fake")
        monkeypatch.setattr("agentic_fabric.core.decomposer.get_runtime_spec", lambda framework: FakeSpec())
        monkeypatch.setattr("agentic_fabric.core.decomposer.importlib.import_module", lambda module_name: fake_module)

        assert isinstance(get_runner(), FakeRunner)

    def test_get_runner_wraps_unknown_framework(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Unknown framework names should include registered options."""

        def fake_get_runtime_spec(framework: str):
            raise ValueError("unknown")

        monkeypatch.setattr("agentic_fabric.core.decomposer.get_runtime_spec", fake_get_runtime_spec)

        with pytest.raises(ValueError, match="Unknown framework: unknown"):
            get_runner("unknown")

    def test_is_cli_runner_available_handles_available_and_missing_profiles(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """CLI availability should map runner errors to False."""

        class FakeCliRunner:
            def is_available(self) -> bool:
                return True

        monkeypatch.setattr("agentic_fabric.core.decomposer.get_cli_runner", lambda profile: FakeCliRunner())
        assert is_cli_runner_available("ok") is True

        monkeypatch.setattr(
            "agentic_fabric.core.decomposer.get_cli_runner",
            lambda profile: (_ for _ in ()).throw(ValueError("missing")),
        )
        assert is_cli_runner_available("missing") is False

    def test_decompose_crew_enforces_required_runtime_and_builds(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Required framework configs should build through that runtime."""

        class FakeRunner:
            def build_crew(self, crew_config):
                return {"built": crew_config}

        monkeypatch.setattr("agentic_fabric.core.decomposer.is_framework_available", lambda framework: True)
        monkeypatch.setattr("agentic_fabric.core.decomposer.get_runner", lambda framework: FakeRunner())

        crew_config = {"required_framework": "crewai", "name": "reviewer"}

        assert decompose_crew(crew_config, framework="auto") == {"built": crew_config}

    def test_decompose_crew_reports_conflicting_or_missing_required_runtime(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Required runtime errors should surface clear guidance."""
        crew_config = {"required_framework": "crewai"}

        with pytest.raises(ValueError, match="Crew requires crewai"):
            decompose_crew(crew_config, framework="strands")

        monkeypatch.setattr("agentic_fabric.core.decomposer.is_framework_available", lambda framework: False)

        with pytest.raises(RuntimeError, match="pip install crewai"):
            decompose_crew(crew_config)

    def test_run_crew_auto_enforces_required_runtime_and_runs(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """run_crew_auto should build and run through the selected runner."""

        class FakeRunner:
            def build_crew(self, crew_config):
                return {"crew": crew_config}

            def run(self, crew, inputs):
                return f"{crew['crew']['name']}:{inputs['task']}"

        monkeypatch.setattr("agentic_fabric.core.decomposer.is_framework_available", lambda framework: True)
        monkeypatch.setattr("agentic_fabric.core.decomposer.get_runner", lambda framework: FakeRunner())

        result = run_crew_auto({"name": "reviewer", "required_framework": "langgraph"}, {"task": "go"})

        assert result == "reviewer:go"

    def test_run_crew_auto_reports_conflicting_or_missing_required_runtime(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """run_crew_auto should reject conflicts and unavailable required runtimes."""
        crew_config = {"required_framework": "langgraph"}

        with pytest.raises(ValueError, match="Crew requires langgraph"):
            run_crew_auto(crew_config, framework="crewai")

        monkeypatch.setattr("agentic_fabric.core.decomposer.is_framework_available", lambda framework: False)

        with pytest.raises(RuntimeError, match=r"agentic-fabric\[langgraph\]"):
            run_crew_auto(crew_config)


class TestFrameworkInfo:
    """Tests for lazy runtime registry metadata."""

    def setup_method(self):
        """Clear the framework cache before each test."""
        _framework_cache.clear()
        clear_runtime_cache()

    def test_framework_info_includes_install_guidance(self) -> None:
        """Runtime registry metadata should expose extras and availability."""
        with patch("agentic_fabric.runners.registry.importlib.import_module", side_effect=ImportError("missing")):
            info = get_framework_info("crewai")

        assert isinstance(info, dict)
        assert info["name"] == "crewai"
        assert info["extra"] is None
        assert info["available"] is False
        assert info["install"] == "pip install crewai"


class TestGetInstallCommand:
    """Tests for _get_install_command."""

    def test_crewai_is_external_install(self) -> None:
        assert _get_install_command("crewai") == "pip install crewai"

    def test_langgraph_includes_langchain(self) -> None:
        assert _get_install_command("langgraph") == 'pip install "agentic-fabric[langgraph]"'

    def test_strands_maps_correctly(self) -> None:
        assert _get_install_command("strands") == 'pip install "agentic-fabric[strands]"'

    def test_unknown_framework_returns_itself(self) -> None:
        """Unknown framework name should return as-is."""
        result = _get_install_command("unknown_framework")
        assert result == "pip install unknown_framework"
