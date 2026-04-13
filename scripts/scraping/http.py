"""Async HTTP client with concurrency control, retry, and paginated fetching."""

import asyncio
import re

import aiohttp
from bs4 import BeautifulSoup

from .config import REQUEST_DELAY, REQUEST_TIMEOUT, MAX_RETRIES, DEFAULT_CONCURRENCY


class HttpClient:
    """Rate-limited async HTTP client with built-in retry and pagination support."""

    def __init__(self, concurrency: int = DEFAULT_CONCURRENCY):
        self._concurrency = concurrency
        self._semaphore = asyncio.Semaphore(concurrency)
        self._session: aiohttp.ClientSession | None = None

    async def __aenter__(self):
        self._session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=REQUEST_TIMEOUT)
        )
        return self

    async def __aexit__(self, *exc):
        if self._session:
            await self._session.close()
            self._session = None

    async def fetch(self, url: str) -> str:
        """Fetch a URL with semaphore rate limiting and exponential backoff retry."""
        async with self._semaphore:
            await asyncio.sleep(REQUEST_DELAY)
            return await self._fetch_with_retry(url)

    async def fetch_paginated(self, initial_url: str, page_url_template: str) -> str:
        """Fetch a paginated search result, returning all pages concatenated.

        Uses a dedicated session per call because Vanderbilt's pagination
        relies on server-side session state.
        """
        async with self._semaphore:
            await asyncio.sleep(REQUEST_DELAY)
            return await self._fetch_all_pages(initial_url, page_url_template)

    async def _fetch_with_retry(self, url: str) -> str:
        last_exc = None
        delay = REQUEST_DELAY
        for attempt in range(MAX_RETRIES + 1):
            try:
                async with self._session.get(url) as resp:
                    return await resp.text()
            except Exception as exc:
                last_exc = exc
                if attempt < MAX_RETRIES:
                    await asyncio.sleep(delay)
                    delay *= 2
        raise last_exc

    async def _fetch_all_pages(self, initial_url: str, page_url_template: str) -> str:
        async with aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=REQUEST_TIMEOUT)
        ) as session:
            async with session.get(initial_url) as resp:
                content = await resp.read()

            total = _parse_total_records(content)
            additional_pages = max(0, total // 50 - (not (total % 50)))

            for page_num in range(2, additional_pages + 2):
                async with session.get(page_url_template.format(page_num)) as resp:
                    content += await resp.read()

            return content.decode("utf-8", errors="replace")


def _parse_total_records(content: bytes) -> int:
    soup = BeautifulSoup(content, "lxml")
    script = soup.find("script", string=re.compile("totalRecords"))
    if not script:
        return 0
    match = re.search(r"totalRecords\s*:\s*(\d+)", script.string)
    return int(match.group(1)) if match else 0
