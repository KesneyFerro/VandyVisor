"""Discover all courses from the historical catalog by searching each subject."""

from __future__ import annotations

import re

from tqdm.asyncio import tqdm

from ..config import CATALOG_SEARCH_URL, SUBJECT_MAP
from ..http import HttpClient


async def discover_catalog(client: HttpClient) -> list[dict]:
    """Search every subject in SUBJECT_MAP and collect (course_id, offer_num) pairs."""
    subjects = list(SUBJECT_MAP.items())
    results: list[dict] = []
    failed: list[tuple[str, str]] = []

    tasks = [_fetch_subject(client, name, code) for name, code in subjects]
    for coro in tqdm.as_completed(tasks, desc="Discovering catalog", total=len(tasks)):
        name, code, entries, success = await coro
        if success:
            results.extend(entries)
        else:
            failed.append((name, code))

    if failed:
        print(f"\nRetrying {len(failed)} failed subject(s)...")
        retry_tasks = [_fetch_subject(client, n, c) for n, c in failed]
        for coro in tqdm.as_completed(retry_tasks, desc="Retrying", total=len(retry_tasks)):
            name, code, entries, success = await coro
            if success:
                results.extend(entries)
            else:
                print(f"Retry failed for subject '{code}'")

    return results


async def _fetch_subject(
    client: HttpClient, subject_name: str, subject_code: str
) -> tuple[str, str, list[dict], bool]:
    try:
        url = CATALOG_SEARCH_URL.format(subject_name)
        html = await client.fetch(url)

        if "No courses found." in html:
            return subject_name, subject_code, [], True

        entries = _parse_course_ids(html, subject_code)
        return subject_name, subject_code, entries, True
    except Exception as exc:
        print(f"Error discovering subject '{subject_code}': {exc}")
        return subject_name, subject_code, [], False


def _parse_course_ids(html: str, subject_code: str) -> list[dict]:
    id_pattern = re.compile(
        r"YAHOO\.mis\.student\.CourseDetailPanel\.showCourseDetail\("
        r"'(\d+)',\s*'(\d+)',\s*notificationString\);"
    )
    notif_pattern = re.compile(r"var notificationString = '(.*?)';")

    ids = id_pattern.findall(html)
    notifications = notif_pattern.findall(html)

    results = []
    for i, (course_id, offer_num) in enumerate(ids):
        # Verify this course belongs to the searched subject
        verification_code = None
        if i < len(notifications):
            match = re.match(r"^(.*?)-\d+$", notifications[i])
            verification_code = match.group(1) if match else None

        if verification_code != subject_code:
            continue

        results.append({
            "course_id": course_id,
            "offer_num": offer_num,
            "subject_code": subject_code,
        })

    return results
