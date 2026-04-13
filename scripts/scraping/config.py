"""Scraping configuration: URLs, constants, and mapping re-exports."""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "config"))
from mappings import SCHOOL_MAP, CAREER_MAP, COMPONENT_MAP, SUBJECT_MAP, ATTRIBUTE_MAP

SECTION_SEARCH_URL = "https://more.app.vanderbilt.edu/more/SearchClassesExecute!search.action?keywords={}"
SECTION_PAGE_URL = "https://more.app.vanderbilt.edu/more/SearchClassesExecute!switchPage.action?pageNum={}"
SECTION_DETAIL_URL = "https://more.app.vanderbilt.edu/more/GetClassSectionDetail.action?classNumber={}&termCode={}"

CATALOG_SEARCH_URL = "https://more.app.vanderbilt.edu/more/SearchCoursesExecute!search.action?keywords={}"
CATALOG_DETAIL_URL = "https://more.app.vanderbilt.edu/more/GetCourseDetail.action?id={}&offerNumber={}"

DEFAULT_CONCURRENCY = 20
DEFAULT_BATCH_SIZE = 500
REQUEST_DELAY = 0.3
REQUEST_TIMEOUT = 10
MAX_RETRIES = 2

HIGH_VOLUME_KEYWORDS = [100, 110, 385, 799, 850, 899]
