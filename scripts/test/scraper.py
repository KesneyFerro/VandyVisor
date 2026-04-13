import argparse
import asyncio
from listings import iterate_keywords
from details import iterate_listings

def main():
    parser = argparse.ArgumentParser(description="Scrape course listings and details.")

    parser.add_argument('-l', '--listings', action='store_true', help="Scrape course listings only")
    parser.add_argument('-d', '--details', action='store_true', help="Scrape course details only")
    parser.add_argument('-c', '--concurrent', type=int, default=6,
                        help="Maximum number of concurrent requests (default: 6)")
    parser.add_argument('-b', '--batch-size', type=int, default=1000,
                        help="Number of listings to process before writing to disk (default: 1000)")

    args = parser.parse_args()

    # If neither flag is passed, run both functions
    if not (args.listings or args.details):
        asyncio.run(iterate_keywords(max_concurrent=args.concurrent))
        asyncio.run(iterate_listings(max_concurrent=args.concurrent, batch_size=args.batch_size))
    else:
        if args.listings:
            asyncio.run(iterate_keywords(max_concurrent=args.concurrent))

        if args.details:
            asyncio.run(iterate_listings(max_concurrent=args.concurrent, batch_size=args.batch_size))

if __name__ == "__main__":
    main() 