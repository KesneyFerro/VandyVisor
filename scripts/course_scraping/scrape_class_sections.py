"""
Scrape Vanderbilt class section details.

This module scrapes class section information from Vanderbilt's course system
by iterating through class numbers and extracting detailed information.
"""

import requests
from bs4 import BeautifulSoup
import pandas as pd
import re
import time
from typing import Dict, List, Optional
import sys
import os

# Add the config directory to the path for imports
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'config'))

from mappings import SCHOOL_MAP, CAREER_MAP, COMPONENT_MAP


# Configuration constants
BASE_URL = "https://more.app.vanderbilt.edu/more/GetClassSectionDetail.action"
TERM_CODE = "1055"
START_CLASS_NUMBER = 1000
END_CLASS_NUMBER = 13000
REQUEST_DELAY = 0.05  # Seconds between requests
REQUEST_TIMEOUT = 2   # Seconds for request timeout


def parse_class_header(header_text: str) -> Optional[Dict[str, str]]:
    """
    Parse class header to extract subject, catalog number, and section.
    
    Args:
        header_text: The header text from the class detail page
        
    Returns:
        Dictionary with parsed components or None if parsing fails
    """
    # Split by colon to separate course code from title
    split_parts = re.split(r"\s*:\s*", header_text, maxsplit=1)
    left_part = split_parts[0].strip()
    long_title = split_parts[1].strip() if len(split_parts) > 1 else ""

    # Extract course components using regex
    match = re.match(r"([A-Z]{2,6})-([A-Z\d]{4,6})-(\d{2})", left_part)
    if not match:
        return None

    subject, catalog_number, section_number = match.groups()
    display_name = f"{subject}-{catalog_number}"

    return {
        "subject": subject,
        "catalog_number": catalog_number,
        "section_number": section_number,
        "display_name": display_name,
        "long_title": long_title
    }


def extract_class_details(soup: BeautifulSoup) -> Dict[str, Optional[str]]:
    """
    Extract class details from the parsed HTML.
    
    Args:
        soup: BeautifulSoup object of the class detail page
        
    Returns:
        Dictionary with extracted class details
    """
    detail_panel = soup.find("div", {"class": "detailPanel"})
    if not detail_panel:
        return {}

    rows = detail_panel.find_all("tr")
    school, career, component, hours = None, None, None, None

    for row in rows:
        tds = row.find_all("td")
        if len(tds) < 2:
            continue
            
        label = tds[0].get_text(strip=True).replace(":", "")
        value = tds[1].get_text(strip=True)

        if label == "School":
            school = SCHOOL_MAP.get(value)
        elif label == "Career":
            career = CAREER_MAP.get(value)
        elif label == "Component":
            component = COMPONENT_MAP.get(value)
        elif label == "Hours":
            try:
                hours = float(value)
            except ValueError:
                hours = None

    return {
        "school_code": school,
        "career_code": career,
        "component_code": component,
        "units_earned": hours
    }


def scrape_class_section(class_number: int) -> Optional[Dict]:
    """
    Scrape details for a single class section.
    
    Args:
        class_number: The class number to scrape
        
    Returns:
        Dictionary with class information or None if scraping fails
    """
    url = (f"{BASE_URL}?classNumber={class_number}"
           f"&termCode={TERM_CODE}&hideAddToCartButton=false")
    
    try:
        response = requests.get(url, timeout=REQUEST_TIMEOUT)
        
        # Check if response contains class section details
        if "classSectionDetailDialog" not in response.text:
            return None

        soup = BeautifulSoup(response.text, "html.parser")
        h1 = soup.find("h1")
        
        if h1 is None:
            return None

        header_text = h1.get_text(separator=" ").strip()
        
        # Parse the header
        parsed_header = parse_class_header(header_text)
        if not parsed_header:
            return None

        # Extract additional details
        class_details = extract_class_details(soup)

        # Combine all information
        result = {
            "class_number": str(class_number),
            "display_name": parsed_header["display_name"],
            "long_title": parsed_header["long_title"],
            "subject": parsed_header["subject"],
            "catalog_number": parsed_header["catalog_number"],
            "section_number": parsed_header["section_number"],
            **class_details
        }

        return result

    except requests.RequestException:
        return None
    except Exception:
        return None


def main():
    """Main function to scrape all class sections and save to CSV."""
    print("Starting Vanderbilt class section scraping...")
    print(f"Scanning class numbers {START_CLASS_NUMBER} to {END_CLASS_NUMBER}")
    
    results = []
    successful_count = 0

    for class_number in range(START_CLASS_NUMBER, END_CLASS_NUMBER):
        class_data = scrape_class_section(class_number)
        
        if class_data:
            successful_count += 1
            results.append(class_data)
            print(f"Found class {class_number:5d} - Total found: {successful_count:05d}")
        
        # Add delay to avoid overwhelming the server
        time.sleep(REQUEST_DELAY)

    # Save results to CSV
    if results:
        df = pd.DataFrame(results)
        output_file = "../../data/processed/course_catalog/vanderbilt_class_data.csv"
        df.to_csv(output_file, index=False)
        print(f"Successfully saved {len(results)} classes to {output_file}")
    else:
        print("No class data found")


if __name__ == "__main__":
    main()
