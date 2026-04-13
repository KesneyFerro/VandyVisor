"""Parse class section detail HTML into structured data."""

import re

from bs4 import BeautifulSoup

from ..config import SCHOOL_MAP, CAREER_MAP, COMPONENT_MAP


def parse_section(html: str, term_code: str) -> dict:
    """Parse a GetClassSectionDetail response into a flat dictionary."""
    soup = BeautifulSoup(html, "lxml")

    class_num_div = soup.find("div", class_="classNumber")
    if not class_num_div:
        raise ValueError("Missing classNumber element")

    class_number = class_num_div.text.split(":")[1].strip()
    dept, code, section, title = _parse_header(soup)
    details = _parse_details_table(soup)
    description, notes = _parse_description(soup)
    status, capacity, enrolled, wl_cap, wl_occ = _parse_availability(soup)
    attributes = _parse_attributes(soup)
    days, times, dates, instructors = _parse_meetings(soup)

    return {
        "id": f"cn{class_number}tc{term_code}",
        "course_dept": dept,
        "course_code": code,
        "class_section": section,
        "course_title": title,
        **details,
        "description": description,
        "notes": notes,
        "status": status,
        "capacity": capacity,
        "enrolled": enrolled,
        "wl_capacity": wl_cap,
        "wl_occupied": wl_occ,
        "attributes": attributes,
        "meeting_days": days,
        "meeting_times": times,
        "meeting_dates": dates,
        "instructors": instructors,
    }


def _parse_header(soup: BeautifulSoup) -> tuple[str, str, str, str]:
    h1 = soup.find("h1")
    if not h1:
        raise ValueError("Missing h1 header")

    text = h1.get_text(separator=" ").strip()
    match = re.match(r"([A-Z]{2,6})-([A-Z\d]{4,6})-(\d{2})\s*:\s*(.*)", text)
    if match:
        return match.group(1), match.group(2), match.group(3), match.group(4).strip()

    # Fallback: split-based parsing
    parts = text.split(":", 1)
    codes = parts[0].split("-")
    title = parts[1].strip() if len(parts) > 1 else ""
    return codes[0].strip(), codes[1].strip(), codes[2].strip(), title


def _parse_details_table(soup: BeautifulSoup) -> dict:
    table = soup.find("table", class_="nameValueTable")
    if not table:
        return {}

    fields = {}
    mapping = {
        "School:": ("school", SCHOOL_MAP),
        "Career:": ("career", CAREER_MAP),
        "Component:": ("class_type", COMPONENT_MAP),
    }

    for label_text, (key, code_map) in mapping.items():
        td = table.find("td", string=label_text)
        if td:
            raw = td.find_next_sibling("td").text.strip()
            fields[key] = code_map.get(raw, raw)

    simple = {
        "Hours:": "credit_hours",
        "Grading Basis:": "grading_basis",
        "Consent:": "consent",
        "Session:": "session",
        "Session Dates:": "dates",
        "Requirement(s):": "requirements",
    }
    for label_text, key in simple.items():
        td = table.find("td", string=label_text)
        if td:
            fields[key] = td.find_next_sibling("td").text.strip()

    term_td = table.find("td", string="Term:")
    if term_td:
        term_text = term_td.find_next_sibling("td").text.strip()
        parts = term_text.split(" ", 1)
        fields["term_year"] = parts[0]
        fields["term_season"] = parts[1] if len(parts) > 1 else ""

    return fields


def _parse_description(soup: BeautifulSoup) -> tuple[str | None, str | None]:
    desc_hdr = soup.find("div", class_="detailHeader", string=lambda t: t and "Description" in t)
    description = desc_hdr.find_next_sibling("div").text.strip() if desc_hdr else None

    notes_hdr = soup.find("div", class_="detailHeader", string=lambda t: t and "Notes" in t)
    notes = notes_hdr.find_next_sibling("div").text.strip() if notes_hdr else None

    return description, notes


def _parse_availability(soup: BeautifulSoup) -> tuple[str, str, str, str, str]:
    indicator = soup.find("div", class_="availabiltyIndicator")
    status = indicator.find("span").text.strip() if indicator else "Unknown"

    table = soup.find("table", class_="availabilityNameValueTable")
    if not table:
        return status, "0", "0", "0", "0"

    def _val(label: str) -> str:
        td = table.find("td", string=label)
        return td.find_next_sibling("td").text.strip() if td else "0"

    return (
        status,
        _val("Class Capacity:"),
        _val("Total Enrolled:"),
        _val("Wait List Capacity:"),
        _val("Total on Wait List:"),
    )


def _parse_attributes(soup: BeautifulSoup) -> list[str] | None:
    hdr = soup.find("div", class_="detailHeader", string=lambda t: t and "Attributes" in t)
    if not hdr:
        return None
    items = hdr.find_next_sibling("div").find_all("div", class_="listItem")
    return [item.text.strip() for item in items]


def _parse_meetings(soup: BeautifulSoup) -> tuple[list, list, list, list]:
    tables = soup.find_all("table", class_="meetingPatternTable")
    days, times, dates = [], [], []
    instructor_set: set[str] = set()

    for table in tables:
        for row in table.find_all("tr")[1:]:
            cols = row.find_all("td")
            if len(cols) < 5:
                continue
            days.append(cols[0].text.strip())
            times.append(cols[1].text.strip())
            dates.append(cols[3].text.strip())
            for div in cols[4].find_all("div"):
                instructor_set.add(div.text.strip())

    instructors = _format_instructors(instructor_set)
    return days, times, dates, instructors


def _format_instructors(raw: set[str]) -> list[str]:
    parsed = []
    for name in raw:
        is_primary = name.endswith("(Primary)")
        clean = name.replace("(Primary)", "").strip()
        parsed.append((is_primary, clean))

    parsed.sort(key=lambda x: (not x[0], x[1]))
    return [name if primary else f"{name} (Secondary)" for primary, name in parsed]
