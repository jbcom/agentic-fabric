"""Tests for single-agent CLI runners."""

from __future__ import annotations

import os
import subprocess

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from agentic_fabric.runners.local_cli_runner import LocalCLIConfig, LocalCLIRunner
from agentic_fabric.runners.single_agent_runner import SingleAgentRunner


class TestSingleAgentRunner:
    """Test the SingleAgentRunner base class."""

    def test_is_abstract(self):
        """SingleAgentRunner should be abstract."""
        with pytest.raises(TypeError):
            SingleAgentRunner()

    def test_default_is_available(self):
        """is_available is now abstract — subclasses must implement it."""

        class TestRunner(SingleAgentRunner):
            def run(self, task: str, working_dir: str | None = None, **kwargs):
                return "test"

            def is_available(self) -> bool:
                return True

        runner = TestRunner()
        assert runner.is_available() is True

    def test_default_get_required_env_vars(self):
        """Default get_required_env_vars should return empty list."""

        class TestRunner(SingleAgentRunner):
            def run(self, task: str, working_dir: str | None = None, **kwargs):
                return "test"

            def is_available(self) -> bool:
                return True

        runner = TestRunner()
        assert runner.get_required_env_vars() == []


class TestLocalCLIConfig:
    """Test the LocalCLIConfig dataclass."""

    def test_minimal_config(self):
        """Should create config with minimal required fields."""
        config = LocalCLIConfig(
            command="test-tool",
            task_flag="--task",
        )

        assert config.command == "test-tool"
        assert config.task_flag == "--task"
        assert config.auth_env == []
        assert config.timeout == 300

    def test_full_config(self):
        """Should create config with all fields."""
        config = LocalCLIConfig(
            command="aider",
            task_flag="--message",
            subcommand=None,
            auth_env=["OPENAI_API_KEY"],
            auto_approve="--yes-always",
            structured_output="--json",
            model_flag="--model",
            default_model="gpt-4o",
            working_dir_flag="--cwd",
            additional_flags=["--no-git"],
            timeout=600,
            name="Aider",
            description="AI pair programming",
            install_cmd="pipx install aider-chat",
        )

        assert config.command == "aider"
        assert config.auth_env == ["OPENAI_API_KEY"]
        assert config.auto_approve == "--yes-always"
        assert config.timeout == 600


class TestLocalCLIRunner:
    """Test the LocalCLIRunner implementation."""

    @pytest.fixture
    def mock_profiles_file(self, tmp_path: Path):
        """Create a temporary profiles YAML file."""
        profiles_content = """
profiles:
  test-tool:
    name: "Test Tool"
    description: "A test tool"
    command: "test-tool"
    task_flag: "--task"
    auth_env:
      - "TEST_API_KEY"
    auto_approve: "--yes"
    timeout: 120
    install_cmd: "pip install test-tool"

  aider:
    name: "Aider"
    description: "AI pair programming"
    command: "aider"
    task_flag: "--message"
    auth_env:
      - "OPENAI_API_KEY"
    auto_approve: "--yes-always"
    model_flag: "--model"
    additional_flags:
      - "--no-git"
    timeout: 300
    install_cmd: "pipx install aider-chat"
"""
        profiles_file = tmp_path / "local_cli_profiles.yaml"
        profiles_file.write_text(profiles_content)
        return profiles_file

    def test_load_profiles(self, mock_profiles_file: Path):
        """Should load profiles from YAML file."""
        with patch("agentic_fabric.runners.local_cli_runner.Path") as mock_path:
            mock_path.return_value.parent = mock_profiles_file.parent
            mock_path.return_value.__truediv__.return_value = mock_profiles_file

            # Clear cache
            LocalCLIRunner._profiles_cache = None

            profiles = LocalCLIRunner._load_profiles()

            assert "test-tool" in profiles
            assert "aider" in profiles
            assert profiles["test-tool"].command == "test-tool"
            assert profiles["aider"].auth_env == ["OPENAI_API_KEY"]

    @pytest.mark.skipif(os.name != "posix", reason="POSIX file mode check")
    def test_rejects_group_writable_profiles_file(self, mock_profiles_file: Path):
        """Bundled local CLI profiles should not be group or world writable."""
        mock_profiles_file.chmod(0o664)
        with patch("agentic_fabric.runners.local_cli_runner.Path") as mock_path:
            mock_path.return_value.parent = mock_profiles_file.parent
            mock_path.return_value.__truediv__.return_value = mock_profiles_file

            LocalCLIRunner._profiles_cache = None

            with pytest.raises(PermissionError, match="writable by group or other"):
                LocalCLIRunner._load_profiles()

    def test_profiles_permission_check_is_noop_on_non_posix(self, mock_profiles_file: Path):
        """Non-POSIX platforms should skip POSIX mode checks."""
        from agentic_fabric.runners import local_cli_runner

        with patch.object(local_cli_runner.os, "name", "nt"):
            local_cli_runner._validate_profiles_file_permissions(mock_profiles_file)

    def test_init_with_profile_name(self, mock_profiles_file: Path):
        """Should initialize with a profile name."""
        with patch("agentic_fabric.runners.local_cli_runner.Path") as mock_path:
            mock_path.return_value.parent = mock_profiles_file.parent
            mock_path.return_value.__truediv__.return_value = mock_profiles_file

            LocalCLIRunner._profiles_cache = None

            runner = LocalCLIRunner("aider")

            assert runner.config.command == "aider"
            assert runner.config.task_flag == "--message"

    def test_named_profile_receives_isolated_config_copy(self, mock_profiles_file: Path):
        """Mutating one named runner should not mutate the cached profile."""
        with patch("agentic_fabric.runners.local_cli_runner.Path") as mock_path:
            mock_path.return_value.parent = mock_profiles_file.parent
            mock_path.return_value.__truediv__.return_value = mock_profiles_file

            LocalCLIRunner._profiles_cache = None
            runner = LocalCLIRunner("aider")

            runner.config.auth_env.append("MUTATED")
            runner.config.additional_flags.append("--mutated")

            cached = LocalCLIRunner._load_profiles()["aider"]
            assert cached.auth_env == ["OPENAI_API_KEY"]
            assert cached.additional_flags == ["--no-git"]

    def test_init_with_unknown_profile(self, mock_profiles_file: Path):
        """Should raise ValueError for unknown profile."""
        with patch("agentic_fabric.runners.local_cli_runner.Path") as mock_path:
            mock_path.return_value.parent = mock_profiles_file.parent
            mock_path.return_value.__truediv__.return_value = mock_profiles_file

            LocalCLIRunner._profiles_cache = None

            with pytest.raises(ValueError, match="Unknown profile"):
                LocalCLIRunner("unknown-tool")

    def test_init_with_config_dict(self):
        """Should initialize with a config dict."""
        config_dict = {
            "command": "my-tool",
            "task_flag": "--prompt",
            "auto_approve": "--yes",
        }

        runner = LocalCLIRunner(config_dict)

        assert runner.config.command == "my-tool"
        assert runner.config.task_flag == "--prompt"
        assert runner.config.auto_approve == "--yes"

    def test_rejects_unknown_config_dict_fields(self):
        """Custom config dicts should reject unsupported fields."""
        with pytest.raises(ValueError, match="unsupported fields"):
            LocalCLIRunner({"command": "my-tool", "task_flag": "--prompt", "shell": True})

    @pytest.mark.parametrize(
        "config,error_type,match",
        [
            ({"command": "", "task_flag": "--prompt"}, ValueError, "non-empty command"),
            ({"command": "my-tool", "task_flag": None}, TypeError, "task_flag as a string"),
        ],
    )
    def test_rejects_invalid_required_scalar_fields(self, config, error_type, match):
        """Required scalar profile fields should have strict types."""
        with pytest.raises(error_type, match=match):
            LocalCLIRunner(config)

    def test_rejects_shell_operator_in_command(self):
        """Profile commands should be direct executable invocations."""
        with pytest.raises(ValueError, match="direct executable"):
            LocalCLIRunner({"command": "my-tool && rm -rf /", "task_flag": "--prompt"})

    @pytest.mark.parametrize(
        "field_name,value",
        [
            ("auto_approve", "   "),
            ("structured_output", '--json "unterminated'),
            ("task_flag", "--prompt; rm -rf /"),
            ("subcommand", "run && rm -rf /"),
            ("auto_approve", "--yes | sh"),
            ("structured_output", "--json > out"),
            ("model_flag", "--model $(touch bad)"),
            ("default_model", "model;touch-bad"),
            ("working_dir_flag", "--cwd\n--bad"),
        ],
    )
    def test_rejects_shell_control_in_config_cli_fields(self, field_name, value):
        """Config-controlled CLI fragments should stay single safe arguments."""
        config = {"command": "my-tool", "task_flag": "--prompt", field_name: value}

        with pytest.raises(ValueError, match=field_name):
            LocalCLIRunner(config)

    def test_rejects_invalid_additional_flags(self):
        """List fields should contain only non-empty strings."""
        with pytest.raises(ValueError, match="additional_flags"):
            LocalCLIRunner({"command": "my-tool", "task_flag": "--prompt", "additional_flags": ["--ok", ""]})

        with pytest.raises(ValueError, match="additional_flags"):
            LocalCLIRunner({"command": "my-tool", "task_flag": "--prompt", "additional_flags": ["--ok", "--bad;"]})

    def test_rejects_invalid_auth_env_names(self):
        """Auth env names should be valid environment variable identifiers."""
        with pytest.raises(ValueError, match="auth_env"):
            LocalCLIRunner({"command": "my-tool", "task_flag": "--prompt", "auth_env": ["OK", "BAD-NAME"]})

    def test_rejects_invalid_optional_scalar_field(self):
        """Optional string fields should reject non-string values."""
        with pytest.raises(ValueError, match="working_dir_flag"):
            LocalCLIRunner({"command": "my-tool", "task_flag": "--prompt", "working_dir_flag": 123})

    def test_rejects_invalid_timeout(self):
        """Timeouts should stay within the bounded execution range."""
        with pytest.raises(ValueError, match="timeout"):
            LocalCLIRunner({"command": "my-tool", "task_flag": "--prompt", "timeout": 0})

    def test_load_profiles_reports_missing_profiles_file(self, tmp_path: Path):
        """Missing bundled profiles should raise clear guidance."""
        missing_profiles_file = tmp_path / "local_cli_profiles.yaml"
        with patch("agentic_fabric.runners.local_cli_runner.Path") as mock_path:
            mock_path.return_value.parent = tmp_path
            mock_path.return_value.__truediv__.return_value = missing_profiles_file

            LocalCLIRunner._profiles_cache = None

            with pytest.raises(FileNotFoundError, match=r"Expected local_cli_profiles\.yaml"):
                LocalCLIRunner._load_profiles()

    def test_load_profiles_rejects_non_mapping_yaml(self, tmp_path: Path):
        """Profiles YAML must have a mapping root and mapping profiles section."""
        profiles_file = tmp_path / "local_cli_profiles.yaml"
        profiles_file.write_text("- not\n- a mapping\n", encoding="utf-8")
        with patch("agentic_fabric.runners.local_cli_runner.Path") as mock_path:
            mock_path.return_value.parent = tmp_path
            mock_path.return_value.__truediv__.return_value = profiles_file

            LocalCLIRunner._profiles_cache = None

            with pytest.raises(TypeError, match="must contain a mapping"):
                LocalCLIRunner._load_profiles()

    def test_load_profiles_rejects_non_mapping_profiles_section(self, tmp_path: Path):
        """Profiles YAML must define profiles as a mapping."""
        profiles_file = tmp_path / "local_cli_profiles.yaml"
        profiles_file.write_text("profiles:\n  - not-a-mapping\n", encoding="utf-8")
        with patch("agentic_fabric.runners.local_cli_runner.Path") as mock_path:
            mock_path.return_value.parent = tmp_path
            mock_path.return_value.__truediv__.return_value = profiles_file

            LocalCLIRunner._profiles_cache = None

            with pytest.raises(TypeError, match="profiles"):
                LocalCLIRunner._load_profiles()

    def test_load_profiles_rejects_symlink_profiles_file(self, tmp_path: Path):
        """Bundled profiles should be read from a regular file."""
        target_file = tmp_path / "target.yaml"
        target_file.write_text("profiles: {}\n", encoding="utf-8")
        profiles_file = tmp_path / "local_cli_profiles.yaml"
        profiles_file.symlink_to(target_file)

        with patch("agentic_fabric.runners.local_cli_runner.Path") as mock_path:
            mock_path.return_value.parent = tmp_path
            mock_path.return_value.__truediv__.return_value = profiles_file

            LocalCLIRunner._profiles_cache = None

            with pytest.raises(FileNotFoundError, match="regular file"):
                LocalCLIRunner._load_profiles()

    def test_profiles_source_rejects_unexpected_file_name(self, tmp_path: Path):
        """The bundled profiles source should have the expected file name."""
        from agentic_fabric.runners import local_cli_runner

        unexpected_file = tmp_path / "profiles.yaml"
        unexpected_file.write_text("profiles: {}\n", encoding="utf-8")

        with pytest.raises(ValueError, match="Unexpected profiles file name"):
            local_cli_runner._validate_profiles_file_source(unexpected_file)

    def test_load_profiles_rejects_invalid_profile_entries(self, tmp_path: Path):
        """Profiles YAML should contain string names mapped to config mappings."""
        profiles_file = tmp_path / "local_cli_profiles.yaml"
        profiles_file.write_text("profiles:\n  bad: not-a-mapping\n", encoding="utf-8")

        with patch("agentic_fabric.runners.local_cli_runner.Path") as mock_path:
            mock_path.return_value.parent = tmp_path
            mock_path.return_value.__truediv__.return_value = profiles_file

            LocalCLIRunner._profiles_cache = None

            with pytest.raises(TypeError, match="invalid profile entry"):
                LocalCLIRunner._load_profiles()

    def test_init_with_config_object(self):
        """Should initialize with a LocalCLIConfig object."""
        config = LocalCLIConfig(
            command="custom-tool",
            task_flag="--task",
        )

        runner = LocalCLIRunner(config)

        assert runner.config.command == "custom-tool"
        assert runner.config.task_flag == "--task"

    def test_init_with_config_object_uses_profile_validation(self):
        """LocalCLIConfig objects should not bypass fragment validation."""
        config = LocalCLIConfig(
            command="custom-tool",
            task_flag="--task; rm -rf /",
        )

        with pytest.raises(ValueError, match="task_flag"):
            LocalCLIRunner(config)

    def test_init_rejects_unsupported_profile_input(self):
        """Unsupported profile inputs should fail with a clear type error."""
        with pytest.raises(TypeError, match="profile must be"):
            LocalCLIRunner(["not", "supported"])

    def test_is_available_tool_exists(self):
        """Should return True if tool is in PATH."""
        config = LocalCLIConfig(command="python", task_flag="--task")
        runner = LocalCLIRunner(config)

        assert runner.is_available() is True

    def test_is_available_tool_missing(self):
        """Should return False if tool is not in PATH."""
        config = LocalCLIConfig(command="nonexistent-tool-xyz", task_flag="--task")
        runner = LocalCLIRunner(config)

        assert runner.is_available() is False

    def test_get_required_env_vars(self):
        """Should return required env vars from config."""
        config = LocalCLIConfig(
            command="test",
            task_flag="--task",
            auth_env=["API_KEY", "SECRET"],
        )
        runner = LocalCLIRunner(config)

        assert runner.get_required_env_vars() == ["API_KEY", "SECRET"]

    def test_run_missing_env_vars(self):
        """Should raise RuntimeError if required env vars missing."""
        config = LocalCLIConfig(
            command="test",
            task_flag="--task",
            auth_env=["MISSING_ENV_VAR"],
        )
        runner = LocalCLIRunner(config)

        with pytest.raises(RuntimeError, match="Missing required environment variables"):
            runner.run("test task")

    def test_run_rejects_nul_task_argument(self):
        """User arguments should be valid subprocess arguments."""
        config = LocalCLIConfig(command="test-tool", task_flag="--task")
        runner = LocalCLIRunner(config)

        with pytest.raises(ValueError, match="NUL byte"):
            runner.run("safe\x00unsafe")

    def test_run_rejects_non_string_runtime_arguments(self):
        """Runtime arguments should be strings before reaching subprocess."""
        config = LocalCLIConfig(command="test-tool", task_flag="--task")
        runner = LocalCLIRunner(config)

        with pytest.raises(TypeError, match="task must be a string"):
            runner.run(123)  # type: ignore[arg-type]

    @patch.dict("os.environ", {"TEST_API_KEY": "test-key"})
    @patch("subprocess.run")
    def test_run_success(self, mock_run: MagicMock):
        """Should execute command successfully."""
        config = LocalCLIConfig(
            command="test-tool",
            task_flag="--task",
            auth_env=["TEST_API_KEY"],
        )
        runner = LocalCLIRunner(config)

        # Mock successful execution
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="Test output",
            stderr="",
        )

        result = runner.run("Fix the bug")

        assert result == "Test output"
        mock_run.assert_called_once()

        # Check command was built correctly
        call_args = mock_run.call_args
        assert call_args[0][0] == ["test-tool", "--task", "Fix the bug"]
        assert call_args.kwargs["shell"] is False

    @patch.dict("os.environ", {"TEST_API_KEY": "test-key"})
    @patch("subprocess.run")
    def test_run_with_auto_approve(self, mock_run: MagicMock):
        """Should include auto-approve flag when enabled."""
        config = LocalCLIConfig(
            command="test-tool",
            task_flag="--task",
            auth_env=["TEST_API_KEY"],
            auto_approve="--yes",
        )
        runner = LocalCLIRunner(config)

        mock_run.return_value = MagicMock(returncode=0, stdout="Output", stderr="")

        runner.run("Test task", auto_approve=True)

        call_args = mock_run.call_args
        assert "--yes" in call_args[0][0]

    @patch.dict("os.environ", {"TEST_API_KEY": "test-key"})
    @patch("subprocess.run")
    def test_run_with_structured_output(self, mock_run: MagicMock):
        """Should include structured output flag when enabled."""
        config = LocalCLIConfig(
            command="test-tool",
            task_flag="--task",
            auth_env=["TEST_API_KEY"],
            structured_output="--output-format json",
        )
        runner = LocalCLIRunner(config)

        mock_run.return_value = MagicMock(returncode=0, stdout="Output", stderr="")

        runner.run("Test task", structured_output=True)

        call_args = mock_run.call_args
        assert call_args[0][0] == ["test-tool", "--task", "Test task", "--output-format", "json"]

    @patch.dict("os.environ", {"TEST_API_KEY": "test-key"})
    @patch("subprocess.run")
    def test_run_with_model(self, mock_run: MagicMock):
        """Should include model flag when model specified."""
        config = LocalCLIConfig(
            command="test-tool",
            task_flag="--task",
            auth_env=["TEST_API_KEY"],
            model_flag="--model",
        )
        runner = LocalCLIRunner(config)

        mock_run.return_value = MagicMock(returncode=0, stdout="Output", stderr="")

        runner.run("Test task", model="gpt-4o")

        call_args = mock_run.call_args
        cmd = call_args[0][0]
        assert "--model" in cmd
        assert "gpt-4o" in cmd

    @patch.dict("os.environ", {"TEST_API_KEY": "test-key"})
    @patch("subprocess.run")
    def test_run_with_additional_flags(self, mock_run: MagicMock):
        """Should include additional flags from config."""
        config = LocalCLIConfig(
            command="test-tool",
            task_flag="--task",
            auth_env=["TEST_API_KEY"],
            additional_flags=["--no-cache", "--log-level debug"],
        )
        runner = LocalCLIRunner(config)

        mock_run.return_value = MagicMock(returncode=0, stdout="Output", stderr="")

        runner.run("Test task")

        call_args = mock_run.call_args
        cmd = call_args[0][0]
        assert "--no-cache" in cmd
        assert "--log-level" in cmd
        assert "debug" in cmd

    @patch.dict("os.environ", {"TEST_API_KEY": "test-key"})
    @patch("subprocess.run")
    def test_run_failure(self, mock_run: MagicMock):
        """Should raise RuntimeError on command failure."""
        config = LocalCLIConfig(
            command="test-tool",
            task_flag="--task",
            auth_env=["TEST_API_KEY"],
        )
        runner = LocalCLIRunner(config)

        # Mock failed execution with CalledProcessError (raised when check=True)
        mock_run.side_effect = subprocess.CalledProcessError(
            returncode=1,
            cmd=["test-tool", "--task", "Test task"],
            output="",
            stderr="Error occurred",
        )

        with pytest.raises(RuntimeError, match="Command failed with exit code 1"):
            runner.run("Test task")

    @patch.dict("os.environ", {"TEST_API_KEY": "test-key"})
    @patch("subprocess.run")
    def test_run_timeout(self, mock_run: MagicMock):
        """Should raise RuntimeError on timeout."""
        config = LocalCLIConfig(
            command="test-tool",
            task_flag="--task",
            auth_env=["TEST_API_KEY"],
            timeout=1,
        )
        runner = LocalCLIRunner(config)

        # Mock timeout
        mock_run.side_effect = subprocess.TimeoutExpired("test-tool", 1)

        with pytest.raises(RuntimeError, match="Command timed out"):
            runner.run("Test task")

    @patch.dict("os.environ", {"TEST_API_KEY": "test-key"})
    @patch("subprocess.run")
    def test_build_command_positional_task(self, mock_run: MagicMock):
        """Should handle positional task argument (no flag)."""
        # Note: command can contain spaces and will be split with shlex
        # But using subcommand/default_model is more explicit (see next test)
        config = LocalCLIConfig(
            command="test-tool",
            task_flag="",  # Positional
            auth_env=["TEST_API_KEY"],
        )
        runner = LocalCLIRunner(config)

        mock_run.return_value = MagicMock(returncode=0, stdout="Output", stderr="")

        runner.run("Fix the bug")

        call_args = mock_run.call_args
        cmd = call_args[0][0]
        # Should be: ["test-tool", "Fix the bug"]
        assert cmd == ["test-tool", "Fix the bug"]
        assert "--task" not in cmd

    @patch.dict("os.environ", {"TEST_API_KEY": "test-key"})
    @patch("subprocess.run")
    def test_build_command_with_subcommand(self, mock_run: MagicMock):
        """Should include subcommand if specified."""
        config = LocalCLIConfig(
            command="ollama",
            subcommand="run",
            task_flag="",
            auth_env=["TEST_API_KEY"],
            default_model="codellama",
        )
        runner = LocalCLIRunner(config)

        mock_run.return_value = MagicMock(returncode=0, stdout="Output", stderr="")

        runner.run("Test task")

        call_args = mock_run.call_args
        cmd = call_args[0][0]
        assert cmd[0] == "ollama"
        assert cmd[1] == "run"
        assert "codellama" in cmd

    @patch.dict("os.environ", {"TEST_API_KEY": "test-key"})
    @patch("subprocess.run")
    def test_build_command_with_positional_model_and_working_dir_flag(self, mock_run: MagicMock):
        """Positional models and supported working-dir flags should be included."""
        config = LocalCLIConfig(
            command="ollama",
            subcommand="run",
            task_flag="",
            auth_env=["TEST_API_KEY"],
            working_dir_flag="--cwd",
        )
        runner = LocalCLIRunner(config, model="deepseek-coder")

        mock_run.return_value = MagicMock(returncode=0, stdout="Output", stderr="")

        runner.run("Test task", working_dir="/tmp/work")

        cmd = mock_run.call_args[0][0]
        assert cmd == ["ollama", "run", "deepseek-coder", "Test task", "--cwd", "/tmp/work"]
