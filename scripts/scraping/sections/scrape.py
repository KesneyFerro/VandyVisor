"""Orchestrate section discovery and detail scraping."""

import os

from tqdm.asyncio import tqdm

from ..config import SECTION_DETAIL_URL, DEFAULT_CONCURRENCY, DEFAULT_BATCH_SIZE
from ..http import HttpClient
from ..storage import DataStore, load_json, save_json
from .discover import discover_sections
from .parse import parse_section


async def scrape_sections(
    concurrency: int = DEFAULT_CONCURRENCY,
    batch_size: int = DEFAULT_BATCH_SIZE,
    term_code: str | None = None,
    discover_only: bool = False,
    scrape_only: bool = False,
    output_dir: str = "data",
):
    listings_path = os.path.join(output_dir, "section_listings.json")
    data_path = os.path.join(output_dir, "sections.json")

    async with HttpClient(concurrency) as client:
        if not scrape_only:
            listings = await discover_sections(client)
            save_json(listings, listings_path)
            print(f"Discovered {len(listings)} unique sections")
            if discover_only:
                return

        listings = load_json(listings_path)
        if not listings:
            print("No section listings found. Run discovery first.")
            return

        store = DataStore(data_path)
        failed: list[dict] = []

        tasks = [
            _fetch_section(client, entry, term_code)
            for entry in listings
        ]

        for coro in tqdm.as_completed(tasks, desc="Scraping sections", total=len(tasks)):
            entry, parsed, success = await coro
            if success:
                store.update([parsed])
                if store.auto_flush(batch_size):
                    pass
            else:
                failed.append(entry)

        store.flush()

        if failed:
            print(f"\nRetrying {len(failed)} failed section(s)...")
            retry_tasks = [_fetch_section(client, e, term_code) for e in failed]
            for coro in tqdm.as_completed(retry_tasks, desc="Retrying", total=len(retry_tasks)):
                entry, parsed, success = await coro
                if success:
                    store.update([parsed])
                else:
                    print(f"Retry failed: class {entry['class_number']}")
            store.flush()

    print(f"Done. {store.count} total sections in {data_path}")


async def _fetch_section(
    client: HttpClient, entry: dict, term_code_override: str | None
) -> tuple[dict, dict | None, bool]:
    tc = term_code_override or entry["term_code"]
    url = SECTION_DETAIL_URL.format(entry["class_number"], tc)
    try:
        html = await client.fetch(url)
        parsed = parse_section(html, tc)
        return entry, parsed, True
    except Exception as exc:
        return entry, None, False
