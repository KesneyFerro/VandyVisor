import os
import aiohttp
import asyncio
import re
import json
from datetime import datetime
from bs4 import BeautifulSoup
from tqdm.asyncio import tqdm

def find_total_records(soup):
    """
    A simple helper function to find total records that pop up for a given search result.

    Parameters:
    soup (BeautifulSoup object): 

    Returns:
    int: total number of records
    """
    script_tag = soup.find('script', string=re.compile('totalRecords'))

    total_records = 0
    if script_tag:
        match = re.search(r'totalRecords\s*:\s*(\d+)', script_tag.string)
        if match: 
            total_records = int(match.group(1))
    
    return total_records

async def fetch(url):
    """
    A simple async fetch function to extract data from a url (with search keywords encoded).

    Parameters:
    url (string): url to extract data from

    Returns:
    BeautifulSoup object: extracted info from url
    """
    # Create a new session context for this specific search to maintain state
    async with aiohttp.ClientSession() as search_session:
        # First, get the initial search URL
        async with search_session.get(url) as response:
            content = await response.read()

        total_records = find_total_records(BeautifulSoup(content, "lxml"))
        if total_records == 300:
            print("NOTE: MAX RECORD COUNT HIT WITH URL", url)

        # 0-50 records means no additional pages, 51-100 means 1 additional page, etc.
        additional_pages = max(0, total_records // 50 - (not (total_records % 50))) # note 0 gives -1
        page_url = "https://more.app.vanderbilt.edu/more/SearchClassesExecute!switchPage.action?pageNum="

        # Fetch additional pages SEQUENTIALLY using the same session
        for i in range(additional_pages):
            async with search_session.get(page_url + str(i + 2)) as add_response:
                content += await add_response.read()

        soup = BeautifulSoup(content, "lxml")
        return soup

def scrape_listings_for_keyword(soup, keyword, retry_attempt=0):
    # find all <td> with "classNumber_" in id
    listing_elements = soup.find_all('td', id=lambda x: x and x.startswith("classNumber_"))

    new_data = []
    scraped_at = datetime.now().isoformat()

    for listing in listing_elements:
        onclick_text = listing.get('onclick', '')

        class_number, term_code = None, None
        if "classNumber" in onclick_text and "termCode" in onclick_text:
            class_number = onclick_text.split("classNumber : '")[1].split("'")[0]
            term_code = onclick_text.split("termCode : '")[1].split("'")[0]

        if class_number and term_code:
            new_data.append({
                'classNumber': class_number,
                'termCode': term_code,
                'keyword': keyword,
                'scraped_at': scraped_at,
                'retry_attempt': retry_attempt
            })

    return new_data

def update_course_listings(new_data):
    # load existing data
    try:
        with open('data/course_listings.json', 'r') as file:
            existing_data = json.load(file)
    except FileNotFoundError:
        existing_data = []

    # duplicate detection
    existing_set = set((entry["classNumber"], entry["termCode"]) for entry in existing_data)

    # add unique entries
    for entry in new_data:
        pair = (entry["classNumber"], entry["termCode"])
        if pair not in existing_set:
            existing_data.append(entry)
            existing_set.add(pair)

    # ensure data directory exists
    os.makedirs('data', exist_ok=True)
    with open('data/course_listings.json', 'w') as file:
        json.dump(existing_data, file, indent=4)

async def process_keyword(url, addon, session, semaphore, retry_attempt=0):
    """Process a single keyword with rate limiting. Returns (scraped data, success status, url, addon)."""
    async with semaphore:
        try:
            soup = await fetch(url)
            new_data = scrape_listings_for_keyword(soup, keyword=addon, retry_attempt=retry_attempt)
            return new_data, True, url, addon
        except Exception as e:
            print(f"error scraping listings for keyword '{addon}': {e}")
            return [], False, url, addon

async def iterate_keywords(max_concurrent=10):
    """
    Scrape course listings for all keywords concurrently with retry on failure.

    Parameters:
    max_concurrent (int): Maximum number of concurrent requests (default: 10)
    """
    base_url = "https://more.app.vanderbilt.edu/more/SearchClassesExecute!search.action?keywords="

    edges = [100, 110, 385, 799, 850, 899] # keywords that have over 300 entries (gets truncated)
    # skip *999 series since it's mostly phd dissertation research (7999, 8999, 9999 have 300+ each)

    # Build list of all URLs to fetch
    urls_and_addons = []
    for i in range(999):
        if i in edges:
            addons = [str(j) + f"{i:03d}" for j in range(10)]
        else:
            addons = [f"{i:03d}"]

        for addon in addons:
            url = base_url + addon
            urls_and_addons.append((url, addon))

    # Create semaphore for rate limiting
    semaphore = asyncio.Semaphore(max_concurrent)

    # Collect all results in memory and track failures
    all_new_data = []
    failed_items = []

    # Create aiohttp session
    async with aiohttp.ClientSession() as session:
        # Create tasks for all URLs
        tasks = []
        for url, addon in urls_and_addons:
            task = process_keyword(url, addon, session, semaphore, retry_attempt=0)
            tasks.append(task)

        # Process all tasks with progress bar and collect results
        for coro in tqdm.as_completed(tasks, desc="Generating course listings", unit="keyword", total=len(tasks)):
            data, success, url, addon = await coro
            all_new_data.extend(data)
            if not success:
                failed_items.append((url, addon))

        # Retry failed keywords once
        if failed_items:
            print(f"\nRetrying {len(failed_items)} failed keyword(s)...")
            print(f"Retrying the following failures: {', '.join(addon for _, addon in failed_items)}")
            retry_tasks = []
            for url, addon in failed_items:
                task = process_keyword(url, addon, session, semaphore, retry_attempt=1)
                retry_tasks.append(task)

            for coro in tqdm.as_completed(retry_tasks, desc="Retrying failed keywords", unit="keyword", total=len(retry_tasks)):
                data, success, url, addon = await coro
                all_new_data.extend(data)
                if not success:
                    print(f"Retry also failed for keyword '{addon}'")

    # Write all results once at the end
    print("Writing course listings to file...")
    update_course_listings(all_new_data) 