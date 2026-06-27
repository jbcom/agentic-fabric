"""Discovery module - finds packages with fabric agent configuration directories.

Supports framework-specific configuration directories:
- .fabric/  - framework-agnostic fabric configuration
- .crewai/   - CrewAI-specific configurations (default)
- .langgraph/ - LangGraph-specific configurations
- .strands/  - Strands-specific configurations

The discovery order matches framework priority for auto-detection.
"""

from __future__ import annotations

import logging

from pathlib import Path
from typing import Any

import yaml


logger = logging.getLogger(__name__)

# Framework directory names in priority order
# .fabric is framework-agnostic (can run on any available framework)
# Framework-specific dirs enforce that framework
FRAMEWORK_DIRS = [".fabric", ".crewai", ".langgraph", ".strands"]

# Mapping from directory name to framework name
# .fabric maps to None (framework-agnostic, auto-detect at runtime)
DIR_TO_FRAMEWORK: dict[str, str | None] = {
    ".fabric": None,  # Framework-agnostic
    ".crewai": "crewai",
    ".langgraph": "langgraph",
    ".strands": "strands",
}

# Mapping from framework name to directory name
# None (agnostic) maps to .fabric
FRAMEWORK_TO_DIR: dict[str | None, str] = {
    None: ".fabric",
    "crewai": ".crewai",
    "langgraph": ".langgraph",
    "strands": ".strands",
}


def get_workspace_root() -> Path:
    """Get the workspace root directory.

    Walks up from the current file to find the root (where pyproject.toml is).
    """
    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / "pyproject.toml").exists() and (parent / "packages").exists():
            return parent
    # Fallback to current working directory
    return Path.cwd()


def discover_packages(
    workspace_root: Path | None = None,
    framework: str | None = None,
) -> dict[str, Path]:
    """Discover all packages with fabric agent configuration directories.

    Args:
        workspace_root: Root of the workspace. If None, auto-detected.
        framework: Optional framework to filter by (crewai, langgraph, strands).
                   If None, returns first found directory per package.

    Returns:
        Dict mapping package name to its config directory path.
    """
    if workspace_root is None:
        workspace_root = get_workspace_root()

    packages = {}

    # Determine which directories to look for
    if framework:
        dir_name = FRAMEWORK_TO_DIR.get(framework)
        dirs_to_check = [dir_name] if dir_name else FRAMEWORK_DIRS
    else:
        dirs_to_check = FRAMEWORK_DIRS

    # Check packages/ directory
    packages_dir = workspace_root / "packages"
    if packages_dir.is_dir():
        for pkg_dir in packages_dir.iterdir():
            if not pkg_dir.is_dir():
                continue

            # Try each framework directory in priority order
            for dir_name in dirs_to_check:
                config_dir = pkg_dir / dir_name
                if config_dir.is_dir() and (config_dir / "manifest.yaml").exists():
                    packages[pkg_dir.name] = config_dir
                    break  # Use first found (highest priority)

    # Also check workspace root for standalone projects
    for dir_name in dirs_to_check:
        config_dir = workspace_root / dir_name
        if config_dir.is_dir() and (config_dir / "manifest.yaml").exists():
            # Use the workspace name or a default
            pkg_name = workspace_root.name or "default"
            if pkg_name not in packages:
                packages[pkg_name] = config_dir
            break

    return packages


def discover_all_framework_configs(
    workspace_root: Path | None = None,
) -> dict[str, dict[str | None, Path]]:
    """Discover all framework-specific config directories for all packages.

    This finds ALL framework directories, not just the first one per package.

    Args:
        workspace_root: Root of the workspace. If None, auto-detected.

    Returns:
        Dict mapping package name to dict of framework -> config_dir.
        Example: {"sample": {"crewai": Path(...), "strands": Path(...)}}
        Framework can be None for framework-agnostic .fabric/ directories.
    """
    if workspace_root is None:
        workspace_root = get_workspace_root()

    packages: dict[str, dict[str | None, Path]] = {}

    # Check packages/ directory
    packages_dir = workspace_root / "packages"
    if packages_dir.is_dir():
        for pkg_dir in packages_dir.iterdir():
            if not pkg_dir.is_dir():
                continue

            pkg_configs: dict[str | None, Path] = {}
            for dir_name in FRAMEWORK_DIRS:
                config_dir = pkg_dir / dir_name
                if config_dir.is_dir() and (config_dir / "manifest.yaml").exists():
                    framework = DIR_TO_FRAMEWORK[dir_name]
                    pkg_configs[framework] = config_dir

            if pkg_configs:
                packages[pkg_dir.name] = pkg_configs

    # Also check workspace root
    root_configs: dict[str | None, Path] = {}
    for dir_name in FRAMEWORK_DIRS:
        config_dir = workspace_root / dir_name
        if config_dir.is_dir() and (config_dir / "manifest.yaml").exists():
            framework = DIR_TO_FRAMEWORK[dir_name]
            root_configs[framework] = config_dir

    if root_configs:
        pkg_name = workspace_root.name or "default"
        if pkg_name not in packages:
            packages[pkg_name] = root_configs

    return packages


def load_manifest(config_dir: Path) -> dict[str, Any]:
    """Load a package's fabric manifest.

    Args:
        config_dir: Path to the fabric or runtime-specific config directory.

    Returns:
        Parsed manifest as a dictionary.
    """
    manifest_path = config_dir / "manifest.yaml"
    with open(manifest_path, encoding="utf-8") as f:
        result = yaml.safe_load(f)
        return result or {}


def _resolve_config_path(config_dir: Path, relative_path: str) -> Path:
    """Resolve a manifest path and require it to stay below the config dir."""
    candidate = Path(relative_path)
    if candidate.is_absolute() or ".." in candidate.parts:
        msg = f"Manifest path must be relative to {config_dir.name}: {relative_path}"
        raise ValueError(msg)

    root = config_dir.resolve()
    resolved = (root / candidate).resolve(strict=False)
    if not resolved.is_relative_to(root):
        msg = f"Manifest path escapes config directory: {relative_path}"
        raise ValueError(msg)
    return resolved


def get_framework_from_config_dir(config_dir: Path) -> str | None:
    """Determine the required framework from a config directory path.

    Args:
        config_dir: Path to a framework config directory (.crewai, .strands, etc.)

    Returns:
        Framework name if directory indicates a specific framework, None otherwise.
    """
    dir_name = config_dir.name
    return DIR_TO_FRAMEWORK.get(dir_name)


def get_fabric_agent_config(config_dir: Path, fabric_agent_name: str) -> dict:
    """Load a specific fabric agent's configuration.

    Args:
        config_dir: Path to the config directory (.fabric/, .crewai/, .strands/, .langgraph/).
        fabric_agent_name: Name of the fabric agent to load.

    Returns:
        Dict with agents, tasks, knowledge_paths, and required_framework.
        The required_framework field indicates which framework MUST be used
        if the config is in a framework-specific directory.

    Raises:
        ValueError: If fabric agent not found in manifest.
    """
    manifest = load_manifest(config_dir)
    fabric_agents = manifest.get("fabric_agents", {})
    fabric_agent_config = fabric_agents.get(fabric_agent_name)

    if not fabric_agent_config:
        available = list(fabric_agents.keys())
        raise ValueError(f"Fabric agent '{fabric_agent_name}' not found. Available: {available}")

    agents_rel = fabric_agent_config.get("agents")
    tasks_rel = fabric_agent_config.get("tasks")
    if not agents_rel or not tasks_rel:
        missing = "agents" if not agents_rel else "tasks"
        msg = f"Fabric agent '{fabric_agent_name}' is missing required key: {missing}"
        raise ValueError(msg)

    # Load agents and tasks YAML
    agents_path = _resolve_config_path(config_dir, agents_rel)
    tasks_path = _resolve_config_path(config_dir, tasks_rel)

    agents = yaml.safe_load(agents_path.read_text(encoding="utf-8")) if agents_path.exists() else {}
    tasks = yaml.safe_load(tasks_path.read_text(encoding="utf-8")) if tasks_path.exists() else {}

    # Resolve knowledge paths
    knowledge_paths = []
    for kp in fabric_agent_config.get("knowledge", []):
        full_path = _resolve_config_path(config_dir, kp)
        if full_path.is_dir():
            knowledge_paths.append(full_path)

    # Determine required framework from directory name
    # If config is in .crewai/, it MUST run on CrewAI, etc.
    required_framework = get_framework_from_config_dir(config_dir)

    # Also check manifest-level preferred_framework (can be overridden by dir)
    manifest_framework = fabric_agent_config.get("preferred_framework")
    if (
        manifest_framework
        and manifest_framework != "auto"
        and required_framework
        and manifest_framework != required_framework
    ):
        # Manifest can specify preference, but directory takes precedence
        logger.warning(
            f"Warning: fabric agent '{fabric_agent_name}' specifies preferred_framework={manifest_framework} "
            f"but is in {config_dir.name}/ directory which requires {required_framework}"
        )

    # Get LLM config from manifest
    llm_config = manifest.get("llm", fabric_agent_config.get("llm", {}))

    return {
        "name": fabric_agent_name,
        "description": fabric_agent_config.get("description", ""),
        "agents": agents,
        "tasks": tasks,
        "knowledge_paths": knowledge_paths,
        "manifest": manifest,
        "config_dir": config_dir,
        # Framework enforcement
        "required_framework": required_framework,
        "preferred_framework": manifest_framework,
        # LLM configuration
        "llm": llm_config,
    }


def list_fabric_agents(
    package_name: str | None = None,
    framework: str | None = None,
) -> dict[str, list[dict]]:
    """List all available fabric agents, optionally filtered by package or framework.

    Args:
        package_name: If provided, only list fabric agents for this package.
        framework: If provided, only list fabric agents that can run on this framework.

    Returns:
        Dict mapping package name to list of fabric agent info dicts.
        Each fabric agent dict includes:
        - name: Fabric agent name
        - description: Fabric agent description
        - required_framework: Framework required (if in framework-specific dir)
    """
    packages = discover_packages(framework=framework)
    result = {}

    for pkg_name, config_dir in packages.items():
        if package_name and pkg_name != package_name:
            continue

        manifest = load_manifest(config_dir)
        required_framework = get_framework_from_config_dir(config_dir)

        fabric_agents = []
        for fabric_agent_name, fabric_agent_config in manifest.get("fabric_agents", {}).items():
            fabric_agents.append(
                {
                    "name": fabric_agent_name,
                    "description": fabric_agent_config.get("description", ""),
                    "required_framework": required_framework,
                    "preferred_framework": fabric_agent_config.get("preferred_framework"),
                }
            )
        result[pkg_name] = fabric_agents

    return result
