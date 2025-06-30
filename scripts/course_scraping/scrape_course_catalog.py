"""
Scrape Vanderbilt course catalog information.

This module scrapes detailed course information from Vanderbilt's course catalog
by searching through subjects and extracting comprehensive course data.
"""

import requests
from bs4 import BeautifulSoup
import csv
import re
from html import unescape
from typing import Dict, List, Optional, Tuple
import sys
import os

# Add the config directory to the path for imports
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'config'))

from mappings import SCHOOL_MAP, CAREER_MAP, COMPONENT_MAP, ATTRIBUTE_MAP, SUBJECT_MAP


# Base URLs for course searching and details
BASE_SEARCH_URL = "https://more.app.vanderbilt.edu/more/SearchCoursesExecute!search.action?keywords={}"
BASE_DETAIL_URL = "https://more.app.vanderbilt.edu/more/GetCourseDetail.action?id={}&offerNumber={}"


def extract_course_ids(html: str) -> List[Tuple[str, str, Optional[str], Optional[str]]]:
    """
    Extract course IDs and related information from search results HTML.
    
    Args:
        html: HTML content from course search results
        
    Returns:
        List of tuples containing (course_id, offer_num, notification_string, verification_code)
    """
    pattern = r"YAHOO\.mis\.student\.CourseDetailPanel\.showCourseDetail\('(?P<course_id>\d+)', '(?P<offer_num>\d+)', notificationString\);"
    notification_pattern = r"var notificationString = '(.*?)';"
    
    ids = re.findall(pattern, html)
    notifications = re.findall(notification_pattern, html)

    courses = []
    for i, (course_id, offer_num) in enumerate(ids):
        notification_string = notifications[i] if i < len(notifications) else None

        if notification_string is not None:
            match = re.match(r"^(.*?)-\d+$", notification_string)
            verification_code = match.group(1) if match else None
        else:
            verification_code = None

        courses.append((course_id, offer_num, notification_string, verification_code))

    return courses


def extract_requirement_text(text: str, keyword: str) -> Optional[str]:
    """
    Extract specific requirement text from course requirements.
    
    Args:
        text: Full requirements text
        keyword: Keyword to search for (e.g., "Prerequisite:", "Corequisite:")
        
    Returns:
        Extracted requirement text or None if not found
    """
    if keyword not in text:
        return None
        
    part = text.split(keyword, 1)[1]
    
    # Stop at other requirement keywords
    for other_keyword in ["Corequisite:", "Prerequisite:", "Not open to students who have earned credit for"]:
        if other_keyword != keyword and other_keyword in part:
            part = part.split(other_keyword)[0]
            
    return part.strip(":; ").strip()


def extract_course_details(html: str, subject_code: str, course_id: str) -> Optional[Dict]:
    """
    Extract detailed course information from course detail HTML.
    
    Args:
        html: HTML content from course detail page
        subject_code: Subject code for the course
        course_id: Course ID
        
    Returns:
        Dictionary with course details or None if extraction fails
    """
    soup = BeautifulSoup(html, "html.parser")
    result = {}

    # Extract title information
    title_line = soup.select_one("#courseDetailDialog h1")
    if not title_line:
        return None

    title_text = title_line.text.strip()
    match = re.search(r"(\d{4}[A-Z]?)\s+-\s+", title_text)
    if not match:
        return None

    catalog_number = match.group(1)

    try:
        long_title = title_text.split(f"{catalog_number} - ", 1)[1].strip()
    except IndexError:
        return None

    display_name = f"{subject_code} {catalog_number}"

    result.update({
        "course_id": course_id,
        "subject": subject_code,
        "catalog_number": catalog_number,
        "display_name": display_name,
        "long_title": long_title
    })

    # Extract basic course details
    detail_map = {}
    for row in soup.select(".detailPanel .nameValueTable tr"):
        strong_tag = row.find("strong")
        if strong_tag:
            key = strong_tag.text.strip(":")
            value_cell = row.find_all("td")[1] if len(row.find_all("td")) > 1 else None
            if value_cell:
                detail_map[key] = value_cell.get_text(strip=True)

    result["school_code"] = SCHOOL_MAP.get(detail_map.get("School"))
    result["career_code"] = CAREER_MAP.get(detail_map.get("Career"))
    result["units_earned"] = detail_map.get("Units", "0").strip()

    # Process components
    components = detail_map.get("Components", "")
    components = re.sub(r"\\(.*?\\)", "", components).strip()
    result["component_code"] = COMPONENT_MAP.get(components)

    # Extract enrollment information
    enrollment_map = {}
    for row in soup.select("#rightSection .detailPanel .nameValueTable tr"):
        strong_tag = row.find("strong")
        if strong_tag:
            key = strong_tag.text.strip(":")
            value_cell = row.find_all("td")[1] if len(row.find_all("td")) > 1 else None
            if value_cell:
                enrollment_map[key] = value_cell.get_text(strip=True)

    # Process term offerings
    term = enrollment_map.get("Typically Offered", "")
    terms = []
    if "Fall" in term:
        terms.append("FA")
    if "Spring" in term:
        terms.append("SP")
    if "Summer" in term:
        terms.append("SU")
    if "Alternate Years" in term:
        terms.append("ALT")
    result["term_offered"] = ", ".join(terms)

    # Extract requirements
    requirements_text = enrollment_map.get("Requirement", "")
    result["all_requirements"] = requirements_text if requirements_text else None
    result["corequisites"] = extract_requirement_text(requirements_text, "Corequisite:")
    result["prerequisites"] = extract_requirement_text(requirements_text, "Prerequisite:")
    result["anti_requirements"] = extract_requirement_text(requirements_text, "Not open to students who have earned credit for")

    # Extract attributes
    attr_divs = soup.select("#rightSection .detailPanel td:has(strong:-soup-contains('Attributes')) ~ td div")
    attributes = []
    for div in attr_divs:
        attr_text = unescape(div.text.strip())
        attr_val = ATTRIBUTE_MAP.get(attr_text)
        if attr_val:
            attributes.append(attr_val)
    result["attributes"] = ", ".join(attributes) if attributes else None

    # Extract course description
    clear_div = soup.find("div", class_="clear")
    description_header = clear_div.find_next_sibling("div", class_="detailHeader") if clear_div else None

    if description_header and "Description" in description_header.text:
        description_panel = description_header.find_next_sibling("div", class_="detailPanel")
        result["description"] = description_panel.text.strip() if description_panel else ""
    else:
        result["description"] = ""

    return result


def main():
    """Main function to scrape course catalog and save to CSV."""
    print("Starting Vanderbilt course catalog scraping...")
    
    # Define CSV structure
    csv_keys = [
        "course_id", "subject", "catalog_number", "display_name", "long_title",
        "school_code", "career_code", "component_code", "units_earned", "term_offered",
        "all_requirements", "corequisites", "prerequisites", "anti_requirements",
        "attributes", "description"
    ]

    csv_path = "../../data/processed/course_catalog/vanderbilt_courses.csv"
    total_courses_found = 0

    # Open CSV file for writing
    with open(csv_path, "w", newline='', encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=csv_keys)
        writer.writeheader()

        # Iterate through all subjects
        for subject_name, subject_code in SUBJECT_MAP.items():
            print(f"Processing ({subject_code}) {subject_name}")

            try:
                # Search for courses in this subject
                response = requests.get(BASE_SEARCH_URL.format(subject_name))
                
                if "No courses found." in response.text:
                    print(f"  No courses found for {subject_name}")
                    continue

                course_entries = extract_course_ids(response.text)
                courses_processed = 0

                for course_id, offer_num, notification_string, verification_code in course_entries:
                    # Verify the course belongs to the current subject
                    if verification_code != subject_code:
                        continue

                    try:
                        # Get detailed course information
                        detail_response = requests.get(BASE_DETAIL_URL.format(course_id, offer_num))
                        course_data = extract_course_details(detail_response.text, subject_code, course_id)

                        if course_data:
                            courses_processed += 1
                            total_courses_found += 1
                            print(f"  ({total_courses_found:05d}) Found: {course_data['display_name']}")
                            writer.writerow(course_data)

                    except Exception as e:
                        print(f"  Error processing course {course_id}: {e}")

                print(f"  Completed {subject_name}: {courses_processed} courses found")

            except Exception as e:
                print(f"  Error searching {subject_name}: {e}")

    print(f"Scraping completed. Total courses found: {total_courses_found}")
    print(f"Results saved to {csv_path}")


if __name__ == "__main__":
    main()
