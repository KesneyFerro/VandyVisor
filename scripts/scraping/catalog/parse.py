"""Parse course catalog detail HTML into structured data."""

import re
from html import unescape

from bs4 import BeautifulSoup

from ..config import SCHOOL_MAP, CAREER_MAP, COMPONENT_MAP, ATTRIBUTE_MAP


def parse_catalog_course(html: str, subject_code: str, course_id: str) -> dict | None:
    """Parse a GetCourseDetail response into a flat dictionary."""
    soup = BeautifulSoup(html, "lxml")

    title_el = soup.select_one("#courseDetailDialog h1")
    if not title_el:
        return None

    title_text = title_el.text.strip()
    match = re.search(r"(\d{4}[A-Z]?)\s+-\s+", title_text)
    if not match:
        return None

    catalog_number = match.group(1)
    try:
        long_title = title_text.split(f"{catalog_number} - ", 1)[1].strip()
    except IndexError:
        return None

    detail_map = _extract_table(soup, ".detailPanel .nameValueTable tr")
    enrollment_map = _extract_table(soup, "#rightSection .detailPanel .nameValueTable tr")

    components_raw = detail_map.get("Components", "")
    components_clean = re.sub(r"\(.*?\)", "", components_raw).strip()

    requirements_text = enrollment_map.get("Requirement", "")

    return {
        "course_id": course_id,
        "subject": subject_code,
        "catalog_number": catalog_number,
        "display_name": f"{subject_code} {catalog_number}",
        "long_title": long_title,
        "school_code": SCHOOL_MAP.get(detail_map.get("School")),
        "career_code": CAREER_MAP.get(detail_map.get("Career")),
        "component_code": COMPONENT_MAP.get(components_clean),
        "units_earned": detail_map.get("Units", "0").strip(),
        "term_offered": _parse_term_offerings(enrollment_map.get("Typically Offered", "")),
        "all_requirements": requirements_text or None,
        "prerequisites": _extract_requirement(requirements_text, "Prerequisite:"),
        "corequisites": _extract_requirement(requirements_text, "Corequisite:"),
        "anti_requirements": _extract_requirement(
            requirements_text, "Not open to students who have earned credit for"
        ),
        "attributes": _parse_attributes(soup),
        "description": _parse_description(soup),
    }


def _extract_table(soup: BeautifulSoup, selector: str) -> dict[str, str]:
    result = {}
    for row in soup.select(selector):
        strong = row.find("strong")
        if not strong:
            continue
        key = strong.text.strip(":")
        cells = row.find_all("td")
        if len(cells) > 1:
            result[key] = cells[1].get_text(strip=True)
    return result


def _parse_term_offerings(text: str) -> str:
    terms = []
    if "Fall" in text:
        terms.append("FA")
    if "Spring" in text:
        terms.append("SP")
    if "Summer" in text:
        terms.append("SU")
    if "Alternate Years" in text:
        terms.append("ALT")
    return ", ".join(terms)


def _extract_requirement(text: str, keyword: str) -> str | None:
    if keyword not in text:
        return None
    part = text.split(keyword, 1)[1]
    stop_keywords = [
        "Corequisite:",
        "Prerequisite:",
        "Not open to students who have earned credit for",
    ]
    for stop in stop_keywords:
        if stop != keyword and stop in part:
            part = part.split(stop)[0]
    return part.strip(":; ").strip() or None


def _parse_attributes(soup: BeautifulSoup) -> str | None:
    attr_divs = soup.select(
        "#rightSection .detailPanel td:has(strong:-soup-contains('Attributes')) ~ td div"
    )
    codes = []
    for div in attr_divs:
        raw = unescape(div.text.strip())
        code = ATTRIBUTE_MAP.get(raw)
        if code:
            codes.append(code)
    return ", ".join(codes) if codes else None


def _parse_description(soup: BeautifulSoup) -> str:
    clear_div = soup.find("div", class_="clear")
    if not clear_div:
        return ""
    header = clear_div.find_next_sibling("div", class_="detailHeader")
    if header and "Description" in header.text:
        panel = header.find_next_sibling("div", class_="detailPanel")
        return panel.text.strip() if panel else ""
    return ""
