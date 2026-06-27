"""Website scraping tools for CrewAI-compatible runners."""

from __future__ import annotations

import logging

from collections import deque
from ipaddress import ip_address
from urllib.parse import urljoin, urlparse

import requests

from bs4 import BeautifulSoup


log = logging.getLogger(__name__)

MAX_CRAWL_PAGES = 25
MAX_CRAWL_DEPTH = 2
_ALLOWED_SCHEMES = {"http", "https"}
_BLOCKED_HOSTS = {"localhost"}


def _is_safe_crawl_url(url: str) -> bool:
    """Return whether a URL is safe for direct crawler requests."""
    parsed = urlparse(url)
    if parsed.scheme not in _ALLOWED_SCHEMES or not parsed.hostname:
        return False

    host = parsed.hostname.lower().rstrip(".")
    if host in _BLOCKED_HOSTS or host.endswith(".localhost"):
        return False

    try:
        address = ip_address(host)
    except ValueError:
        return True

    return not (
        address.is_private
        or address.is_loopback
        or address.is_link_local
        or address.is_multicast
        or address.is_reserved
        or address.is_unspecified
    )


class ScrapeWebsiteTool:
    """A small first-party website scraping tool with CrewAI-compatible shape."""

    name: str = "ScrapeWebsiteTool"
    description: str = "Scrape readable content from a URL."

    def _run(self, url: str) -> str:
        """Scrape readable content from one safe HTTP(S) URL."""
        if not _is_safe_crawl_url(url):
            log.warning("Skipping unsafe scrape URL %s", url)
            return ""

        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
        except requests.RequestException:
            log.exception("Error scraping %s", url)
            return ""

        soup = BeautifulSoup(response.content, "html.parser")
        return self._scrape_content(soup)

    def _scrape_content(self, soup: BeautifulSoup) -> str:
        """Scrape readable content from a BeautifulSoup object."""
        for script_or_style in soup(["script", "style"]):
            script_or_style.decompose()
        return " ".join(t.strip() for t in soup.stripped_strings)


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
        if not _is_safe_crawl_url(url):
            log.warning("Skipping unsafe crawl URL %s", url)
            return ""

        scraped_content: list[str] = []
        visited_urls: set[str] = set()
        queued_urls = {url}
        urls_to_visit = deque([(url, 0)])
        base_netloc = urlparse(url).netloc

        while urls_to_visit and len(visited_urls) < MAX_CRAWL_PAGES:
            current_url, depth = urls_to_visit.popleft()
            queued_urls.discard(current_url)
            if current_url in visited_urls:
                continue
            visited_urls.add(current_url)

            try:
                response = requests.get(current_url, timeout=30)
                response.raise_for_status()

                soup = BeautifulSoup(response.content, "html.parser")
                page_content = self._scrape_content(soup)
                if page_content:
                    scraped_content.append(page_content)

                if depth >= MAX_CRAWL_DEPTH:
                    continue

                for link in soup.find_all("a", href=True):
                    next_url = urljoin(current_url, link["href"])
                    if (
                        next_url not in visited_urls
                        and next_url not in queued_urls
                        and len(visited_urls) + len(queued_urls) < MAX_CRAWL_PAGES
                        and urlparse(next_url).netloc == base_netloc
                        and _is_safe_crawl_url(next_url)
                    ):
                        urls_to_visit.append((next_url, depth + 1))
                        queued_urls.add(next_url)

            except requests.RequestException:
                log.exception("Error crawling %s", current_url)

        return " ".join(scraped_content)
