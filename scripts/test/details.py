import json
import traceback
import os
import aiohttp
import asyncio
from bs4 import BeautifulSoup
from tqdm.asyncio import tqdm
from datetime import datetime

def extract_class_details(soup):
    header = soup.find("h1").text.strip()
    parts = header.strip().split(":", 1)
    dept_code, course_title = parts[0].split("-"), parts[1].strip()

    course_dept, course_code, class_section = dept_code[0], dept_code[1], dept_code[2].strip()
    return course_dept, course_code, class_section, course_title

def extract_other_details(soup):
    details_table = soup.find("table", class_="nameValueTable")
    
    # left side details
    school = details_table.find("td", string="School:").find_next_sibling("td").text.strip()
    career = details_table.find("td", string="Career:").find_next_sibling("td").text.strip()
    class_type = details_table.find("td", string="Component:").find_next_sibling("td").text.strip()
    credit_hours = details_table.find("td", string="Hours:").find_next_sibling("td").text.strip()
    grading_basis = details_table.find("td", string="Grading Basis:").find_next_sibling("td").text.strip()
    consent = details_table.find("td", string="Consent:").find_next_sibling("td").text.strip()

    # right side details
    term = details_table.find("td", string="Term:").find_next_sibling("td").text.strip()
    term_year, term_season = term.split(" ")
    session = details_table.find("td", string="Session:").find_next_sibling("td").text.strip()
    dates = details_table.find("td", string="Session Dates:").find_next_sibling("td").text.strip()
    requirements = details_table.find("td", string="Requirement(s):").find_next_sibling("td").text.strip()

    return school, career, class_type, credit_hours, grading_basis, consent, term_year, term_season, session, dates, requirements

def extract_desc_and_notes(soup):
    description_div = soup.find("div", class_="detailHeader", string=lambda text: "Description" in text)
    description = description_div.find_next_sibling("div").text.strip() if description_div else None

    notes_div = soup.find("div", class_="detailHeader", string=lambda text: "Notes" in text)
    notes = notes_div.find_next_sibling("div").text.strip() if notes_div else None

    return description, notes

def extract_availability(soup):
    availability_table = soup.find("table", class_="availabilityNameValueTable")
    status = soup.find("div", class_="availabiltyIndicator").find("span").text.strip()
    capacity = availability_table.find("td", string="Class Capacity:").find_next_sibling("td").text.strip()
    enrolled = availability_table.find("td", string="Total Enrolled:").find_next_sibling("td").text.strip()
    wl_capacity = availability_table.find("td", string="Wait List Capacity:").find_next_sibling("td").text.strip()
    wl_occupied = availability_table.find("td", string="Total on Wait List:").find_next_sibling("td").text.strip()

    return status, capacity, enrolled, wl_capacity, wl_occupied

def extract_attributes(soup):
    attributes_div = soup.find("div", class_="detailHeader", string=lambda text: "Attributes" in text)
    attributes = [item.text.strip() for item in attributes_div.find_next_sibling("div").find_all("div", class_="listItem")] if attributes_div else None
    return attributes

def extract_meetings_and_instructors(soup):
    meeting_tables = soup.find_all("table", class_="meetingPatternTable")

    meeting_days = []
    meeting_times = []
    meeting_dates = []
    instructors = set()

    for meeting_table in meeting_tables:
        for row in meeting_table.find_all("tr")[1:]:
            columns = row.find_all("td")
            if len(columns) < 4: continue # probably bad data
            meeting_days.append(columns[0].text.strip())
            meeting_times.append(columns[1].text.strip())
            meeting_dates.append(columns[3].text.strip())
            for inst in columns[4].find_all("div"): instructors.add(inst.text.strip())
    
    # Helper to check primary status and clean name
    def parse_instructor(name):
        is_primary = name.endswith("(Primary)")
        clean_name = name.replace("(Primary)", "").strip()
        return is_primary, clean_name

    # Convert set to list with metadata
    instructor_list = [parse_instructor(name) for name in instructors]

    # Sort: Primary first, then alphabetical by clean name
    instructor_list.sort(key=lambda x: (not x[0], x[1]))

    # Format for output
    formatted_instructors = [
        f"{name}" if is_primary else f"{name} (Secondary)"
        for is_primary, name in instructor_list
    ]

    return meeting_days, meeting_times, meeting_dates, formatted_instructors

def scrape_course_details(soup, term_code):
    # Validate we got the right page
    if not soup.find("div", class_="classNumber"):
        raise ValueError("Invalid HTML response - missing classNumber element")

    class_number = soup.find("div", class_="classNumber").text.split(":")[1].strip()
    course_dept, course_code, class_section, course_title = extract_class_details(soup)
    school, career, class_type, credit_hours, grading_basis, consent, term_year, term_season, session, dates, requirements = extract_other_details(soup)
    description, notes = extract_desc_and_notes(soup)
    status, capacity, enrolled, wl_capacity, wl_occupied = extract_availability(soup)
    attributes = extract_attributes(soup)
    meeting_days, meeting_times, meeting_dates, instructors = extract_meetings_and_instructors(soup)
    
    current_data = {
        "id": "cn" + class_number + "tc" + term_code,
        "course_dept": course_dept,
        "course_code": course_code,
        "class_section": class_section,
        "course_title": course_title,
        "school": school,
        "career": career,
        "class_type": class_type,
        "credit_hours": credit_hours,
        "grading_basis": grading_basis,
        "consent": consent,
        "term_year": term_year,
        "term_season": term_season,
        "session": session,
        "dates": dates,
        "requirements": requirements,
        "description": description,
        "notes": notes,
        'status': status,
        'capacity': capacity,
        'enrolled': enrolled,
        'wl_capacity': wl_capacity,
        'wl_occupied': wl_occupied,
        "attributes": attributes,
        "meeting_days": meeting_days,
        "meeting_times": meeting_times, 
        "meeting_dates": meeting_dates, 
        "instructors": instructors
    }

    return current_data

def batch_update_course_details(batch_data, existing_data_dict):
    """Update existing data dict with a batch of new entries."""
    for entry in batch_data:
        if entry is not None:  # Skip failed scrapes
            course_id = entry["id"]
            # Only set timestamp for truly new courses
            if course_id in existing_data_dict:
                # Course exists - preserve existing date_added or keep as null
                entry["date_added"] = existing_data_dict[course_id].get("date_added", None)
            else:
                # Brand new course - set current timestamp
                entry["date_added"] = datetime.now().isoformat()
            existing_data_dict[course_id] = entry
    return existing_data_dict

def write_course_details(existing_data_dict):
    """Write the data dict to file."""
    updated_data = list(existing_data_dict.values())
    with open('data/data.json', 'w') as file:
        json.dump(updated_data, file, indent=4)

async def process_listing(listing, session, semaphore, save_failed_html=False):
    """Process a single course listing with rate limiting. Returns (scraped data, success status, listing)."""
    base_url = "https://more.app.vanderbilt.edu/more/GetClassSectionDetail.action?classNumber="
    url = base_url + f"{listing['classNumber']}&termCode={listing['termCode']}"

    async with semaphore:
        await asyncio.sleep(0.3)  # Small delay to avoid rate limiting
        try:
            async with session.get(url) as response:
                html = await response.text()

            soup = BeautifulSoup(html, 'lxml')
            current_data = scrape_course_details(soup, listing['termCode'])
            return current_data, True, listing
        except Exception as e:
            # Save one failed HTML for debugging
            if save_failed_html and not os.path.exists('data/failed_response.html'):
                os.makedirs('data', exist_ok=True)
                with open('data/failed_response.html', 'w') as f:
                    f.write(html if 'html' in locals() else "No HTML captured")
            print(f"error scraping details for listing '{listing}': {e}")
            traceback.print_exc()
            return None, False, listing

async def iterate_listings(max_concurrent=10, batch_size=500):
    """
    Scrape course details for all listings concurrently with periodic batch writes and retry on failure.

    Parameters:
    max_concurrent (int): Maximum number of concurrent requests (default: 10)
    batch_size (int): Number of listings to process before writing to disk (default: 500)
    """
    with open('data/course_listings.json', 'r') as file:
        data = json.load(file)

    # Load existing data once at the start
    try:
        with open('data/data.json', 'r') as file:
            existing_data = json.load(file)
    except FileNotFoundError:
        existing_data = []

    existing_data_dict = {entry["id"]: entry for entry in existing_data}

    # Create semaphore for rate limiting
    semaphore = asyncio.Semaphore(max_concurrent)

    # Batch collection and failure tracking
    current_batch = []
    failed_listings = []
    completed_count = 0

    # Create aiohttp session
    async with aiohttp.ClientSession() as session:
        # Create tasks for all listings
        tasks = []
        for listing in data:
            task = process_listing(listing, session, semaphore, save_failed_html=True)
            tasks.append(task)

        # Process all tasks with progress bar and periodic writes
        for coro in tqdm.as_completed(tasks, desc="Scraping data", unit="listing", total=len(tasks)):
            result_data, success, listing = await coro
            current_batch.append(result_data)
            completed_count += 1

            if not success:
                failed_listings.append(listing)

            # Write batch when we hit batch_size
            if len(current_batch) >= batch_size:
                existing_data_dict = batch_update_course_details(current_batch, existing_data_dict)
                write_course_details(existing_data_dict)
                print(f"\nWrote batch of {len(current_batch)} listings ({completed_count}/{len(tasks)} total)")
                current_batch = []

        # Write any remaining data from first pass
        if current_batch:
            existing_data_dict = batch_update_course_details(current_batch, existing_data_dict)
            write_course_details(existing_data_dict)
            print(f"\nWrote final batch of {len(current_batch)} listings ({completed_count}/{len(tasks)} total)")
            current_batch = []

        # Retry failed listings once
        if failed_listings:
            print(f"\nRetrying {len(failed_listings)} failed listing(s)...")
            print(f"Retrying the following failures: {', '.join('(' + listing['classNumber'] + ', ' + listing['termCode'] + ')' for listing in failed_listings)}")
            retry_tasks = []
            for listing in failed_listings:
                task = process_listing(listing, session, semaphore, save_failed_html=True)
                retry_tasks.append(task)

            for coro in tqdm.as_completed(retry_tasks, desc="Retrying failed listings", unit="listing", total=len(retry_tasks)):
                result_data, success, listing = await coro
                if result_data:
                    current_batch.append(result_data)
                if not success:
                    print(f"Retry also failed for listing '{listing}'")

            # Write retry results
            if current_batch:
                existing_data_dict = batch_update_course_details(current_batch, existing_data_dict)
                write_course_details(existing_data_dict)
                print(f"\nWrote {len(current_batch)} retried listings")