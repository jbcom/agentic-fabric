"""Generate the Sourcey API reference from the two public package surfaces."""

from __future__ import annotations

import argparse
import ast
import difflib
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "docs" / "api-reference.md"
PACKAGES = (
    ("agentic_fabric", ROOT / "packages/agentic-fabric/src/agentic_fabric"),
    (
        "pytest_agentic_fabric",
        ROOT / "packages/pytest-agentic-fabric/src/pytest_agentic_fabric",
    ),
)


@dataclass(frozen=True)
class Export:
    """A public object re-exported by a package initializer."""

    name: str
    module: str
    kind: str
    signature: str
    summary: str


def _literal_list(node: ast.AST) -> list[str]:
    if not isinstance(node, (ast.List, ast.Tuple)):
        raise TypeError("__all__ must be a literal list or tuple")
    values: list[str] = []
    for element in node.elts:
        if not isinstance(element, ast.Constant) or not isinstance(element.value, str):
            raise TypeError("__all__ entries must be literal strings")
        values.append(element.value)
    return values


def _function_signature(node: ast.FunctionDef | ast.AsyncFunctionDef) -> str:
    arguments = ast.unparse(node.args)
    prefix = "async def" if isinstance(node, ast.AsyncFunctionDef) else "def"
    return f"{prefix} {node.name}({arguments})"


def _object_details(module_path: Path, object_name: str) -> tuple[str, str, str]:
    tree = ast.parse(module_path.read_text(encoding="utf-8"), filename=str(module_path))
    for node in tree.body:
        if (
            isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and node.name == object_name
        ):
            return (
                "function",
                _function_signature(node),
                (ast.get_docstring(node) or "").split("\n", 1)[0],
            )
        if isinstance(node, ast.ClassDef) and node.name == object_name:
            return (
                "class",
                f"class {node.name}",
                (ast.get_docstring(node) or "").split("\n", 1)[0],
            )
    return "value", object_name, "Public package value."


def _exports(package: str, package_dir: Path) -> list[Export]:
    initializer = package_dir / "__init__.py"
    tree = ast.parse(initializer.read_text(encoding="utf-8"), filename=str(initializer))
    exported_names: list[str] = []
    imports: dict[str, tuple[str, str]] = {}

    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == "__all__"
            for target in node.targets
        ):
            exported_names = _literal_list(node.value)
        elif isinstance(node, ast.ImportFrom) and node.module:
            for imported in node.names:
                imports[imported.asname or imported.name] = (node.module, imported.name)

    if not exported_names:
        raise ValueError(f"{initializer} has no literal __all__")

    exports: list[Export] = []
    for name in exported_names:
        if name == "__version__":
            exports.append(
                Export(
                    name,
                    package,
                    "value",
                    "__version__: str",
                    "Installed distribution version.",
                )
            )
            continue
        module, object_name = imports.get(name, (package, name))
        module_path = package_dir / (
            module.removeprefix(f"{package}.").replace(".", "/") + ".py"
        )
        if module == package:
            module_path = initializer
        kind, signature, summary = _object_details(module_path, object_name)
        exports.append(
            Export(name, module, kind, signature, summary or "Public package export.")
        )
    return exports


def generate() -> str:
    lines = [
        "---",
        "title: API reference",
        "description: Generated reference for the stable public import surfaces.",
        "---",
        "",
        "# API reference",
        "",
        (
            "This page is generated from the literal `__all__` surfaces of the two published packages. "
            "It intentionally documents only supported imports, and CI fails when this file is stale."
        ),
    ]
    for package, package_dir in PACKAGES:
        lines.extend(["", f"## `{package}`", ""])
        for export in _exports(package, package_dir):
            lines.extend(
                [
                    f"### `{export.name}`",
                    "",
                    f"Declared by `{export.module}` as a {export.kind}.",
                    "",
                    "```python",
                    export.signature,
                    "```",
                    "",
                    export.summary,
                ]
            )
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="fail instead of writing when the output is stale",
    )
    args = parser.parse_args()
    rendered = generate()
    existing = OUTPUT.read_text(encoding="utf-8") if OUTPUT.exists() else ""
    if args.check:
        if existing == rendered:
            return 0
        print(
            "docs/api-reference.md is stale; run python scripts/generate_api_reference.py"
        )
        print(
            "".join(
                difflib.unified_diff(
                    existing.splitlines(True),
                    rendered.splitlines(True),
                    fromfile=str(OUTPUT),
                    tofile="generated",
                )
            )
        )
        return 1
    OUTPUT.write_text(rendered, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
