"""Crawler behavior tests without optional scraping dependencies."""

from __future__ import annotations

import importlib
import sys
import types

from unittest.mock import MagicMock

import pytest


def import_scraping_tools(monkeypatch: pytest.MonkeyPatch) -> types.ModuleType:
    """Import scraping_tools with lightweight optional dependency stand-ins."""
    fake_crewai_tools = types.ModuleType("crewai_tools")
    fake_requests = types.ModuleType("requests")
    fake_bs4 = types.ModuleType("bs4")

    class ScrapeWebsiteTool:
        """Minimal stand-in for crewai_tools.ScrapeWebsiteTool."""

    class RequestError(Exception):
        """Minimal stand-in for requests.RequestException."""

    class FakeLink(dict):
        """BeautifulSoup-like link node for href access."""

    class BeautifulSoup:
        """Minimal parser for the crawler test fixture."""

        def __init__(self, content: bytes, parser: str):
            self.content = content.decode("utf-8")

        def __call__(self, tags: list[str]) -> list[object]:
            return []

        def find_all(self, tag: str, href: bool = False) -> list[FakeLink]:
            if tag == "a" and href and "duplicate-fail" in self.content:
                return [FakeLink(href="/fail"), FakeLink(href="/fail")]
            return []

        @property
        def stripped_strings(self) -> list[str]:
            return ["duplicate-fail"] if "duplicate-fail" in self.content else []

    fake_crewai_tools.ScrapeWebsiteTool = ScrapeWebsiteTool
    fake_requests.RequestException = RequestError
    fake_requests.get = MagicMock()
    fake_bs4.BeautifulSoup = BeautifulSoup

    monkeypatch.setitem(sys.modules, "crewai_tools", fake_crewai_tools)
    monkeypatch.setitem(sys.modules, "requests", fake_requests)
    monkeypatch.setitem(sys.modules, "bs4", fake_bs4)
    sys.modules.pop("agentic_fabric.tools.scraping_tools", None)
    return importlib.import_module("agentic_fabric.tools.scraping_tools")


def test_crawler_marks_failed_url_visited_before_retry(monkeypatch: pytest.MonkeyPatch) -> None:
    """Duplicate failed URLs should not be requested repeatedly."""
    scraping_tools = import_scraping_tools(monkeypatch)
    root_response = MagicMock()
    root_response.content = b"<a href='/fail'>duplicate-fail</a><a href='/fail'>duplicate-fail</a>"
    root_response.raise_for_status.return_value = None

    scraping_tools.requests.get.side_effect = [
        root_response,
        scraping_tools.requests.RequestException("boom"),
    ]

    result = scraping_tools.CrawlWebsiteTool()._run("https://example.test")

    assert "duplicate-fail" in result
    assert scraping_tools.requests.get.call_count == 2
