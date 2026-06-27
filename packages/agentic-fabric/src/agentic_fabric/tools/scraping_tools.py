"""Website scraping tools for CrewAI-compatible runners."""

from __future__ import annotations

import logging

from collections import deque
from urllib.parse import urljoin, urlparse

import requests

from bs4 import BeautifulSoup
from crewai_tools import ScrapeWebsiteTool


log = logging.getLogger(__name__)


class CrawlWebsiteTool(ScrapeWebsiteTool):
    """A tool for crawling a website and scraping its content.

    This tool extends ScrapeWebsiteTool to support crawling multiple pages
    starting from a given URL.
    """

    name: str = "CrawlWebsiteTool"
    description: str = "Crawl a website from a given URL and scrape its content."

    def _run(self, url: str) -> str:
        """Crawls a website and returns the scraped content.

        Args:
            url: The URL to start crawling from.

        Returns:
            The scraped content of the website.
        """
        scraped_content = ""
        visited_urls = set()
        urls_to_visit = deque([url])
        base_netloc = urlparse(url).netloc

        while urls_to_visit:
            current_url = urls_to_visit.popleft()
            if current_url in visited_urls:
                continue
            visited_urls.add(current_url)

            try:
                response = requests.get(current_url, timeout=30)
                response.raise_for_status()

                soup = BeautifulSoup(response.content, "html.parser")
                scraped_content += self._scrape_content(soup)

                for link in soup.find_all("a", href=True):
                    next_url = urljoin(current_url, link["href"])
                    if urlparse(next_url).netloc == base_netloc and next_url not in visited_urls:
                        urls_to_visit.append(next_url)

            except requests.RequestException:
                log.exception("Error crawling %s", current_url)

        return scraped_content

    def _scrape_content(self, soup: BeautifulSoup) -> str:
        """Scrapes the readable content from a BeautifulSoup object."""
        for script_or_style in soup(["script", "style"]):
            script_or_style.decompose()
        return " ".join(t.strip() for t in soup.stripped_strings)
