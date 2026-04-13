"""Unified CLI for Vanderbilt course scraping."""

import argparse
import asyncio

from .config import DEFAULT_CONCURRENCY, DEFAULT_BATCH_SIZE
from .sections.scrape import scrape_sections
from .catalog.scrape import scrape_catalog


def main():
    parser = argparse.ArgumentParser(description="Vanderbilt course scraper")
    sub = parser.add_subparsers(dest="command", required=True)

    shared = argparse.ArgumentParser(add_help=False)
    shared.add_argument("-c", "--concurrency", type=int, default=DEFAULT_CONCURRENCY)
    shared.add_argument("-b", "--batch-size", type=int, default=DEFAULT_BATCH_SIZE)
    shared.add_argument("-o", "--output-dir", default="data")
    shared.add_argument("--discover-only", action="store_true")
    shared.add_argument("--scrape-only", action="store_true")

    sec = sub.add_parser("sections", parents=[shared], help="Scrape current-semester sections")
    sec.add_argument("-t", "--term-code", default=None, help="Override term code")

    sub.add_parser("catalog", parents=[shared], help="Scrape historical course catalog")

    all_p = sub.add_parser("all", parents=[shared], help="Run both scrapers")
    all_p.add_argument("-t", "--term-code", default=None)

    args = parser.parse_args()

    if args.command == "sections":
        asyncio.run(scrape_sections(
            concurrency=args.concurrency,
            batch_size=args.batch_size,
            term_code=args.term_code,
            discover_only=args.discover_only,
            scrape_only=args.scrape_only,
            output_dir=args.output_dir,
        ))
    elif args.command == "catalog":
        asyncio.run(scrape_catalog(
            concurrency=args.concurrency,
            batch_size=args.batch_size,
            discover_only=args.discover_only,
            scrape_only=args.scrape_only,
            output_dir=args.output_dir,
        ))
    elif args.command == "all":
        asyncio.run(scrape_sections(
            concurrency=args.concurrency,
            batch_size=args.batch_size,
            term_code=args.term_code,
            discover_only=args.discover_only,
            scrape_only=args.scrape_only,
            output_dir=args.output_dir,
        ))
        asyncio.run(scrape_catalog(
            concurrency=args.concurrency,
            batch_size=args.batch_size,
            discover_only=args.discover_only,
            scrape_only=args.scrape_only,
            output_dir=args.output_dir,
        ))
