"""Discover current-semester class sections via keyword search."""

from bs4 import BeautifulSoup
from tqdm.asyncio import tqdm

from ..config import SECTION_SEARCH_URL, SECTION_PAGE_URL, HIGH_VOLUME_KEYWORDS
from ..http import HttpClient


async def discover_sections(client: HttpClient) -> list[dict]:
    """Search keywords 000-998 to find all (classNumber, termCode) pairs."""
    keywords = _build_keyword_list()
    seen: set[tuple[str, str]] = set()
    results: list[dict] = []
    failed: list[str] = []

    tasks = [_fetch_keyword(client, kw) for kw in keywords]
    for coro in tqdm.as_completed(tasks, desc="Discovering sections", total=len(tasks)):
        keyword, listings, success = await coro
        if not success:
            failed.append(keyword)
            continue
        for entry in listings:
            pair = (entry["class_number"], entry["term_code"])
            if pair not in seen:
                seen.add(pair)
                results.append(entry)

    if failed:
        print(f"\nRetrying {len(failed)} failed keyword(s)...")
        retry_tasks = [_fetch_keyword(client, kw) for kw in failed]
        for coro in tqdm.as_completed(retry_tasks, desc="Retrying", total=len(retry_tasks)):
            keyword, listings, success = await coro
            if not success:
                print(f"Retry failed for keyword '{keyword}'")
                continue
            for entry in listings:
                pair = (entry["class_number"], entry["term_code"])
                if pair not in seen:
                    seen.add(pair)
                    results.append(entry)

    return results


async def _fetch_keyword(client: HttpClient, keyword: str) -> tuple[str, list[dict], bool]:
    try:
        url = SECTION_SEARCH_URL.format(keyword)
        html = await client.fetch_paginated(url, SECTION_PAGE_URL)
        listings = _parse_listings(html)
        return keyword, listings, True
    except Exception as exc:
        print(f"Error discovering keyword '{keyword}': {exc}")
        return keyword, [], False


def _parse_listings(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "lxml")
    elements = soup.find_all("td", id=lambda x: x and x.startswith("classNumber_"))
    results = []
    for el in elements:
        onclick = el.get("onclick", "")
        if "classNumber" not in onclick or "termCode" not in onclick:
            continue
        class_number = onclick.split("classNumber : '")[1].split("'")[0]
        term_code = onclick.split("termCode : '")[1].split("'")[0]
        results.append({"class_number": class_number, "term_code": term_code})
    return results


def _build_keyword_list() -> list[str]:
    keywords = []
    for i in range(999):
        if i in HIGH_VOLUME_KEYWORDS:
            keywords.extend(f"{j}{i:03d}" for j in range(10))
        else:
            keywords.append(f"{i:03d}")
    return keywords
