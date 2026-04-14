"""Orchestrate catalog discovery and detail scraping."""

from __future__ import annotations

import os

from tqdm.asyncio import tqdm

from ..config import CATALOG_DETAIL_URL, DEFAULT_CONCURRENCY, DEFAULT_BATCH_SIZE
from ..http import HttpClient
from ..storage import DataStore, load_json, save_json
from .discover import discover_catalog
from .parse import parse_catalog_course


async def scrape_catalog(
    concurrency: int = DEFAULT_CONCURRENCY,
    batch_size: int = DEFAULT_BATCH_SIZE,
    discover_only: bool = False,
    scrape_only: bool = False,
    output_dir: str = "data",
):
    listings_path = os.path.join(output_dir, "catalog_listings.json")
    data_path = os.path.join(output_dir, "catalog.json")

    async with HttpClient(concurrency) as client:
        if not scrape_only:
            listings = await discover_catalog(client)
            save_json(listings, listings_path)
            print(f"Discovered {len(listings)} catalog courses")
            if discover_only:
                return

        listings = load_json(listings_path)
        if not listings:
            print("No catalog listings found. Run discovery first.")
            return

        store = DataStore(data_path, id_key="course_id")
        failed: list[dict] = []

        tasks = [_fetch_course(client, entry) for entry in listings]

        for coro in tqdm.as_completed(tasks, desc="Scraping catalog", total=len(tasks)):
            entry, parsed, success = await coro
            if success and parsed:
                store.update([parsed])
                store.auto_flush(batch_size)
            elif not success:
                failed.append(entry)

        store.flush()

        if failed:
            print(f"\nRetrying {len(failed)} failed course(s)...")
            retry_tasks = [_fetch_course(client, e) for e in failed]
            for coro in tqdm.as_completed(retry_tasks, desc="Retrying", total=len(retry_tasks)):
                entry, parsed, success = await coro
                if success and parsed:
                    store.update([parsed])
                else:
                    print(f"Retry failed: course {entry['course_id']}")
            store.flush()

    print(f"Done. {store.count} total catalog courses in {data_path}")


async def _fetch_course(
    client: HttpClient, entry: dict
) -> tuple[dict, dict | None, bool]:
    url = CATALOG_DETAIL_URL.format(entry["course_id"], entry["offer_num"])
    try:
        html = await client.fetch(url)
        parsed = parse_catalog_course(html, entry["subject_code"], entry["course_id"])
        return entry, parsed, True
    except Exception:
        return entry, None, False
