"""
Extract prerequisites, corequisites, and antirequisites from catalog.json
course descriptions using a local LLM via Ollama.

Usage:
    python -m scripts.llm.extract_requirements [options]

Options:
    --model MODEL       Ollama model name (default: qwen2.5:14b)
    --concurrency N     Parallel requests to Ollama (default: 4)
    --limit N           Process only N courses (useful for smoke testing)
    --ollama-url URL    Ollama base URL (default: http://localhost:11434)
    --catalog PATH      Path to catalog.json (default: data/catalog.json)
    --checkpoint PATH   Path to checkpoint file (default: data/catalog_requirements_checkpoint.json)
    --force             Reprocess courses even if already in checkpoint

Example smoke test:
    python -m scripts.llm.extract_requirements --limit 10
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import tempfile
import time
from pathlib import Path

import aiohttp
from tqdm import tqdm

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_CATALOG = REPO_ROOT / "data" / "catalog.json"
DEFAULT_CHECKPOINT = REPO_ROOT / "data" / "catalog_requirements_checkpoint.json"

REQUIREMENT_KEYWORDS = (
    "Prerequisite",
    "Corequisite",
    "No credit for",
    "Not open to",
)

# How many courses to process between checkpoint saves
SAVE_INTERVAL = 100

# ---------------------------------------------------------------------------
# Prompt
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """\
You are an expert academic course requirement parser for Vanderbilt University.
Extract prerequisites, corequisites, and antirequisites from course descriptions
and encode them as boolean expressions.

Rules:
1. Use && for AND (all must be satisfied), || for OR (any one is acceptable).
2. Use parentheses to group OR alternatives within AND sequences.
   Example: "A and (B or C)" → "A && (B || C)"
3. A comma between courses usually means AND; "or" means OR.
   Semicolons separate independent requirement groups (treat as AND between groups).
4. When a course number appears WITHOUT a department prefix (e.g., "2300" in a
   MATH 2610 course description), infer the department from the course's display
   name (e.g., MATH 2610 → prefix is MATH).
5. "Prerequisite or Corequisite: X" → put the expression in BOTH prerequisites
   AND corequisites fields.
6. "No credit for students who have earned credit for X" or
   "Not open to students who have earned credit for X" → anti_requirements.
7. "consent of instructor" → use the literal string "CONSENT" as the value.
8. If no requirement of a type exists, output null (JSON null, not the string "null").
9. Do NOT include credit-hour limits, grade requirements, or free-text notes —
   only structured course identifiers and CONSENT.

Return ONLY a valid JSON object with exactly these three keys:
  "prerequisites", "corequisites", "anti_requirements"
Each value is either a boolean expression string or null.\
"""

FEW_SHOT_EXAMPLES = """\
Examples:

Course: MATH 2610
Description: "...total credit for this course and MATH 2310 or 2500 will not exceed 6 credit hours... Prerequisite or Corequisite: 2300 or 2310. [3]"
Output: {"prerequisites": "MATH 2300 || MATH 2310", "corequisites": "MATH 2300 || MATH 2310", "anti_requirements": null}

Course: CS 4247
Description: "Prerequisites: CS 3250, 3251; MATH 2410 or 2501 or 2600; MATH 2810 or 2820. [3]"
Output: {"prerequisites": "CS 3250 && CS 3251 && (MATH 2410 || MATH 2501 || MATH 2600) && (MATH 2810 || MATH 2820)", "corequisites": null, "anti_requirements": null}

Course: MATH 7610
Description: "(Also listed as MATH 4610) Linear operators on vector spaces... No credit for students who have earned credit for 4610. [3]"
Output: {"prerequisites": null, "corequisites": null, "anti_requirements": "MATH 4610"}

Course: RUSS 1105
Description: "Expansion of grammar... Prerequisite: 1101. Prerequisite or Corequisite: 1102. [2]"
Output: {"prerequisites": "RUSS 1101 && RUSS 1102", "corequisites": "RUSS 1102", "anti_requirements": null}

Course: PSY-GS 8850
Description: "Special topics... Prerequisite: consent of instructor. [3]"
Output: {"prerequisites": "CONSENT", "corequisites": null, "anti_requirements": null}

Course: SSED 3240
Description: "Study of conceptual structure... Corequisite: SCED 3240 and EDUC 3240. [2]"
Output: {"prerequisites": null, "corequisites": "SCED 3240 && EDUC 3240", "anti_requirements": null}

Course: ECON 1500
Description: "...Not open to students who have earned credit for 1510. [3]"
Output: {"prerequisites": null, "corequisites": null, "anti_requirements": "ECON 1510"}

Now extract requirements from:
Course: {display_name}
Description: "{description}"\
"""


def build_user_message(display_name: str, description: str) -> str:
    # Escape any stray quotes in the description to keep the template clean.
    # Use str.replace() instead of .format() because the few-shot examples
    # contain literal JSON braces that would confuse Python's format parser.
    safe_desc = description.replace('"', '\\"')
    return (
        FEW_SHOT_EXAMPLES
        .replace("{display_name}", display_name)
        .replace("{description}", safe_desc)
    )


# ---------------------------------------------------------------------------
# Ollama API helpers
# ---------------------------------------------------------------------------

EMPTY_RESULT = {"prerequisites": None, "corequisites": None, "anti_requirements": None}
EXPECTED_KEYS = set(EMPTY_RESULT.keys())


async def query_ollama(
    session: aiohttp.ClientSession,
    base_url: str,
    model: str,
    display_name: str,
    description: str,
) -> dict:
    """Call the Ollama chat API and return parsed JSON result."""
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": build_user_message(display_name, description)},
        ],
        "format": "json",
        "stream": False,
        "options": {
            "temperature": 0,
            "num_predict": 256,
        },
    }

    try:
        async with session.post(
            f"{base_url}/api/chat",
            json=payload,
            timeout=aiohttp.ClientTimeout(total=120),
        ) as resp:
            resp.raise_for_status()
            data = await resp.json()
            raw_content = data["message"]["content"]
            result = json.loads(raw_content)

            # Validate keys and types
            if not isinstance(result, dict) or not EXPECTED_KEYS.issubset(result.keys()):
                print(
                    f"\n[WARN] {display_name}: unexpected JSON shape: {raw_content[:200]}",
                    file=sys.stderr,
                )
                return EMPTY_RESULT

            # Coerce unexpected non-null/non-string values to None
            clean = {}
            for key in EXPECTED_KEYS:
                val = result.get(key)
                if val is None or (isinstance(val, str) and val.strip()):
                    clean[key] = val if val is None else val.strip()
                else:
                    clean[key] = None

            return clean

    except (aiohttp.ClientError, asyncio.TimeoutError) as exc:
        print(f"\n[ERROR] {display_name}: network error: {exc}", file=sys.stderr)
        return EMPTY_RESULT
    except (json.JSONDecodeError, KeyError) as exc:
        print(f"\n[ERROR] {display_name}: parse error: {exc}", file=sys.stderr)
        return EMPTY_RESULT


# ---------------------------------------------------------------------------
# Filtering
# ---------------------------------------------------------------------------

def has_requirement_text(description: str) -> bool:
    """Return True if the description likely contains requirement information."""
    return any(kw in description for kw in REQUIREMENT_KEYWORDS)


# ---------------------------------------------------------------------------
# Checkpoint helpers
# ---------------------------------------------------------------------------

def load_checkpoint(path: Path) -> set[str]:
    if path.exists():
        with open(path) as f:
            return set(json.load(f))
    return set()


def save_checkpoint(path: Path, processed: set[str]) -> None:
    tmp = path.with_suffix(".tmp")
    with open(tmp, "w") as f:
        json.dump(sorted(processed), f)
    tmp.replace(path)


# ---------------------------------------------------------------------------
# Catalog I/O
# ---------------------------------------------------------------------------

def load_catalog(path: Path) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def save_catalog(path: Path, courses: list[dict]) -> None:
    tmp = path.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(courses, f, indent=2, ensure_ascii=False)
    tmp.replace(path)


# ---------------------------------------------------------------------------
# Core processing loop
# ---------------------------------------------------------------------------

async def process_courses(
    courses: list[dict],
    *,
    base_url: str,
    model: str,
    concurrency: int,
    checkpoint: set[str],
    checkpoint_path: Path,
    catalog_path: Path,
    force: bool,
    limit: int | None,
) -> None:
    # Build work queue: only courses with requirement keywords, not yet processed
    work = [
        c for c in courses
        if has_requirement_text(c.get("description", ""))
        and (force or c["course_id"] not in checkpoint)
    ]

    if limit is not None:
        work = work[:limit]

    total = len(work)
    if total == 0:
        print("Nothing to process (all matching courses already in checkpoint).")
        return

    print(f"Processing {total} courses with model '{model}' (concurrency={concurrency})...")
    print(f"Estimated time: ~{total * 2 / max(concurrency, 1) / 60:.1f} minutes\n")

    # Index courses by course_id for fast in-place updates
    course_index: dict[str, dict] = {c["course_id"]: c for c in courses}

    semaphore = asyncio.Semaphore(concurrency)
    processed_count = 0
    start_time = time.monotonic()

    connector = aiohttp.TCPConnector(limit=concurrency + 2)
    async with aiohttp.ClientSession(connector=connector) as session:

        async def process_one(course: dict) -> None:
            nonlocal processed_count
            display_name = course.get("display_name", "")
            description = course.get("description", "")

            async with semaphore:
                result = await query_ollama(
                    session, base_url, model, display_name, description
                )

            # Update in-place
            course_index[course["course_id"]].update(result)
            checkpoint.add(course["course_id"])
            processed_count += 1

            # Periodic saves
            if processed_count % SAVE_INTERVAL == 0:
                save_catalog(catalog_path, courses)
                save_checkpoint(checkpoint_path, checkpoint)

        with tqdm(total=total, unit="course", dynamic_ncols=True) as pbar:
            tasks = [process_one(c) for c in work]

            async def tracked(coro):
                await coro
                pbar.update(1)
                elapsed = time.monotonic() - start_time
                rate = processed_count / elapsed if elapsed > 0 else 0
                pbar.set_postfix({"rate": f"{rate:.1f}/s"})

            await asyncio.gather(*[tracked(t) for t in tasks])

    # Final save
    save_catalog(catalog_path, courses)
    save_checkpoint(checkpoint_path, checkpoint)

    elapsed = time.monotonic() - start_time
    print(f"\nDone. Processed {processed_count} courses in {elapsed:.1f}s.")


# ---------------------------------------------------------------------------
# Connectivity check
# ---------------------------------------------------------------------------

async def check_ollama(base_url: str, model: str) -> None:
    """Verify Ollama is running and the model is available."""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{base_url}/api/tags",
                timeout=aiohttp.ClientTimeout(total=5),
            ) as resp:
                resp.raise_for_status()
                data = await resp.json()
                available = [m["name"] for m in data.get("models", [])]

        # Ollama model names may include tag suffix (e.g., "qwen2.5:14b")
        matches = [n for n in available if n.startswith(model.split(":")[0])]
        if not matches:
            print(
                f"[WARN] Model '{model}' not found in Ollama. Available: {available}",
                file=sys.stderr,
            )
            print(f"       Run: ollama pull {model}", file=sys.stderr)
            sys.exit(1)

        print(f"Ollama OK. Using model: {model}")

    except (aiohttp.ClientError, asyncio.TimeoutError) as exc:
        print(
            f"[ERROR] Cannot reach Ollama at {base_url}: {exc}\n"
            "        Make sure Ollama is running: ollama serve",
            file=sys.stderr,
        )
        sys.exit(1)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Extract course requirements from catalog.json using a local LLM."
    )
    parser.add_argument("--model", default="qwen2.5:14b", help="Ollama model name")
    parser.add_argument(
        "--concurrency",
        type=int,
        default=1,
        help="Parallel Ollama requests (default 1 — keeps VRAM stable on a single GPU)",
    )
    parser.add_argument(
        "--limit", type=int, default=None, help="Max courses to process (smoke test)"
    )
    parser.add_argument(
        "--ollama-url", default="http://localhost:11434", help="Ollama base URL"
    )
    parser.add_argument(
        "--catalog", type=Path, default=DEFAULT_CATALOG, help="Path to catalog.json"
    )
    parser.add_argument(
        "--checkpoint",
        type=Path,
        default=DEFAULT_CHECKPOINT,
        help="Path to checkpoint JSON file",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Reprocess courses already in checkpoint",
    )
    return parser.parse_args()


async def main_async() -> None:
    args = parse_args()

    await check_ollama(args.ollama_url, args.model)

    print(f"Loading catalog from {args.catalog}...")
    courses = load_catalog(args.catalog)
    print(f"Loaded {len(courses)} courses.")

    checkpoint = load_checkpoint(args.checkpoint)
    if checkpoint:
        print(f"Resuming: {len(checkpoint)} courses already processed.")

    await process_courses(
        courses,
        base_url=args.ollama_url,
        model=args.model,
        concurrency=args.concurrency,
        checkpoint=checkpoint,
        checkpoint_path=args.checkpoint,
        catalog_path=args.catalog,
        force=args.force,
        limit=args.limit,
    )


def main() -> None:
    asyncio.run(main_async())


if __name__ == "__main__":
    main()
