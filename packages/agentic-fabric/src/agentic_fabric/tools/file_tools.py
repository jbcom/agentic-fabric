"""Framework-neutral file manipulation tools for agents.

These tools enable agents to read and write code to specific directories in
workspace package codebases.
"""

from __future__ import annotations

import os

from pathlib import Path
from typing import Any


try:  # pragma: no cover - exercised by consumers that install CrewAI
    from crewai.tools import BaseTool as _BaseTool
except ImportError:

    class _BaseTool:  # type: ignore[no-redef]
        """Minimal base class used when no framework-specific tool base exists."""


def _load_pydantic_schema_helpers() -> tuple[Any, Any]:  # pragma: no cover
    """Return Pydantic helpers when optional schema metadata is available."""
    try:
        from pydantic import BaseModel, Field
    except ImportError:
        return None, None
    return BaseModel, Field


_PYDANTIC_BASE_MODEL, _PYDANTIC_FIELD = _load_pydantic_schema_helpers()


def _find_workspace_root() -> Path | None:
    """Search upward for workspace root (contains pyproject.toml with workspace)."""
    current = Path(__file__).resolve().parent
    for parent in [current, *list(current.parents)]:
        pyproject = parent / "pyproject.toml"
        if pyproject.exists():
            # Check if this is the workspace root (has packages/ directory)
            packages_dir = parent / "packages"
            if packages_dir.exists() and packages_dir.is_dir():
                return parent
    return None


def get_workspace_root(package_name: str | None = None) -> Path:
    """Get the workspace root directory for the target game code package.

    Returns packages/<package_name> as the workspace root, where the game code lives.

    Uses marker file search to find workspace root reliably, regardless of
    where this module is installed or imported from.

    Args:
        package_name: Name of the target package. If not provided,
            uses TARGET_PACKAGE environment variable, or the only package
            directory when the workspace has exactly one package.

    Returns:
        Path to packages/<package_name> directory.
    """
    # Determine the target package name
    if package_name is None:
        package_name = os.environ.get("TARGET_PACKAGE")

    # Find workspace root using marker file search
    workspace_root = _find_workspace_root()
    if workspace_root:
        packages_dir = workspace_root / "packages"
        if package_name is not None:
            target_dir = packages_dir / package_name
            if target_dir.exists():
                return target_dir
        elif packages_dir.is_dir():
            package_dirs = sorted(path for path in packages_dir.iterdir() if path.is_dir())
            if len(package_dirs) == 1:
                return package_dirs[0]

    # Fallback: try environment variable for root directory
    env_root_var = f"{package_name.upper()}_ROOT" if package_name else None
    if env_root_var and env_root_var in os.environ:
        return Path(os.environ[env_root_var]).resolve()

    # Last fallback - current directory (shouldn't happen in normal use)
    return Path.cwd()


# Allowed directories for writing relative to the selected package root.
ALLOWED_WRITE_DIRS = [
    "src/ecs",  # ECS components, world, data
    "src/ecs/data",  # Species definitions, etc.
    "src/ecs/systems",  # ECS systems
    "src/components",  # React/R3F components
    "src/components/ui",  # UI components
    "src/stores",  # Zustand stores
    "src/systems",  # Non-ECS systems
    "src/utils",  # Utility functions
    "src/types",  # TypeScript types
]

# Allowed file extensions
ALLOWED_EXTENSIONS = {".ts", ".tsx", ".json", ".md"}


def _clean_relative_path(path_value: str) -> str:
    """Normalize a user-provided relative path string."""
    clean_path = path_value.strip().replace("\\", "/")
    if not clean_path or clean_path.startswith("/") or ".." in Path(clean_path).parts:
        raise ValueError(f"Path traversal not allowed in '{clean_path}'")
    return clean_path


def _resolve_workspace_path(path_value: str) -> tuple[str, Path]:
    """Resolve a user path and ensure it remains inside the workspace root."""
    clean_path = _clean_relative_path(path_value)
    workspace_root = get_workspace_root().resolve()
    full_path = (workspace_root / clean_path).resolve(strict=False)
    if not full_path.is_relative_to(workspace_root):
        raise ValueError(f"Path '{clean_path}' escapes workspace root")
    return clean_path, full_path


def _is_allowed_write_path(clean_path: str) -> bool:
    """Return whether a normalized path is under an allowed write directory."""
    return any(clean_path == allowed_dir or clean_path.startswith(f"{allowed_dir}/") for allowed_dir in ALLOWED_WRITE_DIRS)


def _build_pydantic_schema(
    name: str,
    doc: str,
    fields_by_description: dict[str, str],
) -> Any:  # pragma: no cover
    """Build optional Pydantic schemas without making Pydantic a core dependency."""
    if _PYDANTIC_BASE_MODEL is None or _PYDANTIC_FIELD is None:
        return None
    namespace: dict[str, Any] = {
        "__annotations__": dict.fromkeys(fields_by_description, str),
        "__doc__": doc,
    }
    for field_name, description in fields_by_description.items():
        namespace[field_name] = _PYDANTIC_FIELD(description=description)
    return type(name, (_PYDANTIC_BASE_MODEL,), namespace)


WriteFileInput = _build_pydantic_schema(
    "WriteFileInput",
    "Input schema for GameCodeWriterTool.",
    {
        "file_path": "Relative path from workspace root (e.g., 'src/ecs/data/NewComponent.ts')",
        "content": "The TypeScript/TSX code content to write",
    },
)


class GameCodeWriterTool(_BaseTool):  # type: ignore[misc,valid-type]
    """Tool for writing code files to a game package codebase.

    This tool is restricted to specific directories to ensure agents
    only modify appropriate parts of the codebase.
    """

    name: str = "Write Game Code File"
    description: str = """
    Write a code file to the target game codebase (e.g., packages/<target_package>).

    The target package is configurable via TARGET_PACKAGE environment variable.

    ALLOWED DIRECTORIES:
    - src/ecs - ECS components, world definition
    - src/ecs/data - Species data, biome configs
    - src/ecs/systems - ECS systems
    - src/components - React Three Fiber components
    - src/components/ui - UI components (menus, HUD)
    - src/stores - Zustand state stores
    - src/systems - Non-ECS game systems
    - src/utils - Utility functions
    - src/types - TypeScript type definitions

    ALLOWED EXTENSIONS: .ts, .tsx, .json, .md

    Example:
        file_path: "src/ecs/data/species.ts"
        content: "export const PREDATOR_SPECIES = { ... }"
    """
    args_schema: Any = WriteFileInput

    def _run(self, file_path: str, content: str) -> str:
        """Write the file content to the specified path."""
        try:
            clean_path, full_path = _resolve_workspace_path(file_path)

            # Check allowed directories
            if not _is_allowed_write_path(clean_path):
                return f"Error: Path '{clean_path}' is not in an allowed directory. Allowed: {ALLOWED_WRITE_DIRS}"

            # Check extension
            ext = Path(clean_path).suffix.lower()
            if ext not in ALLOWED_EXTENSIONS:
                return f"Error: Extension '{ext}' not allowed. Allowed: {ALLOWED_EXTENSIONS}"

            # Create parent directories
            full_path.parent.mkdir(parents=True, exist_ok=True)

            # Write content
            with open(full_path, "w", encoding="utf-8") as f:
                f.write(content)

            return f"Successfully wrote {len(content)} bytes to {clean_path}"

        except PermissionError:
            return f"Error: Permission denied writing to {file_path}"
        except ValueError as e:
            return f"Error: {e!s}"
        except Exception as e:
            return f"Error writing file: {e!s}"


ReadFileInput = _build_pydantic_schema(
    "ReadFileInput",
    "Input schema for GameCodeReaderTool.",
    {"file_path": "Relative path from workspace root (e.g., 'src/ecs/components.ts')"},
)


class GameCodeReaderTool(_BaseTool):  # type: ignore[misc,valid-type]
    """Tool for reading code files from a game package codebase.

    Use this to understand existing patterns before writing new code.
    """

    name: str = "Read Game Code File"
    description: str = """
    Read a code file from the target package's codebase.

    The target package is determined by the TARGET_PACKAGE environment variable.

    Use this tool to:
    - Understand existing patterns
    - See how similar components are structured
    - Check imports and dependencies

    Example:
        file_path: "src/ecs/components.ts"
    """
    args_schema: Any = ReadFileInput

    def _run(self, file_path: str) -> str:
        """Read the file content from the specified path."""
        try:
            clean_path, full_path = _resolve_workspace_path(file_path)

            if not full_path.exists():
                return f"Error: File not found: {clean_path}"

            if not full_path.is_file():
                return f"Error: Path is not a file: {clean_path}"

            # Limit file size
            if full_path.stat().st_size > 100_000:  # 100KB limit
                return f"Error: File too large (>{100_000} bytes)"

            with open(full_path, encoding="utf-8") as f:
                return f.read()

        except PermissionError:
            return f"Error: Permission denied reading {file_path}"
        except ValueError as e:
            return f"Error: {e!s}"
        except Exception as e:
            return f"Error reading file: {e!s}"


ListDirInput = _build_pydantic_schema(
    "ListDirInput",
    "Input schema for DirectoryListTool.",
    {"directory": "Relative directory path from workspace root (e.g., 'src/ecs')"},
)


class DirectoryListTool(_BaseTool):  # type: ignore[misc,valid-type]
    """Tool for listing files in a directory.

    Use this to discover existing files and understand project structure.
    """

    name: str = "List Directory Contents"
    description: str = """
    List files and subdirectories in the target package codebase.

    The target package is determined by the TARGET_PACKAGE environment variable.

    Use this to:
    - Discover existing components
    - Understand project structure
    - Find files to read or reference

    Example:
        directory: "src/ecs/data"
    """
    args_schema: Any = ListDirInput

    def _run(self, directory: str) -> str:
        """List directory contents."""
        try:
            clean_path, full_path = _resolve_workspace_path(directory)

            if not full_path.exists():
                return f"Error: Directory not found: {clean_path}"

            if not full_path.is_dir():
                return f"Error: Path is not a directory: {clean_path}"

            entries = []
            for entry in sorted(full_path.iterdir()):
                if entry.name.startswith("."):
                    continue
                prefix = "📁" if entry.is_dir() else "📄"
                entries.append(f"{prefix} {entry.name}")

            if not entries:
                return f"Directory {clean_path} is empty"

            return f"Contents of {clean_path}:\n" + "\n".join(entries)

        except PermissionError:
            return f"Error: Permission denied accessing {directory}"
        except ValueError as e:
            return f"Error: {e!s}"
        except Exception as e:
            return f"Error listing directory: {e!s}"
