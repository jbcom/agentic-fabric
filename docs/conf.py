"""Sphinx configuration for agentic-fabric."""

from __future__ import annotations


project = "Agentic Fabric"
author = "Jon Bogaty"
copyright = "2026, Jon Bogaty"  # noqa: A001

extensions = [
    "myst_parser",
    "autodoc2",
    "sphinx_copybutton",
]

source_suffix = {
    ".rst": "restructuredtext",
}

templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]
html_theme = "furo"
html_static_path = ["_static"]
html_css_files = ["agentic-fabric.css"]

autodoc2_packages = [
    {
        "path": "../packages/agentic-fabric/src/agentic_fabric",
        "module": "agentic_fabric",
    }
]
autodoc2_output_dir = "apidocs"
autodoc2_render_plugin = "rst"
autodoc2_docstring_parser_regexes = [(r".*", "myst")]
autodoc2_hidden_objects = ["dunder", "private"]
