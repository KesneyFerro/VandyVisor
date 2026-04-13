# VandyVisor

A modern course planning and scheduling system designed to transform the academic advising experience at Vanderbilt University.

## Purpose

VandyVisor aims to create a more visual and intuitive version of the current advising system. By better organizing course data and degree requirements, this project will provide students with a streamlined way to discover relevant courses and match them to their academic schedules. The goal is to make the schedule planning process significantly easier and more efficient for Vanderbilt students.

The system serves as a comprehensive platform to help students:

1. Visualize their degree progress and requirements
2. Discover courses that fit their academic plans
3. Understand prerequisites and course relationships
4. Optimize their path to graduation

## Current Capabilities

- **Async Course Scraping**: Two distinct scraping pipelines running 20 concurrent requests with retry logic and batch checkpointing:
  - **Sections scraper**: Discovers and scrapes current-semester class sections (enrollment, instructors, meeting times, availability)
  - **Catalog scraper**: Discovers and scrapes the historical course catalog (descriptions, prerequisites, attributes, term offerings)
- **Degree Requirements Processing**: Conversion and analysis of degree requirement data into structured formats
- **Data Analysis**: Jupyter notebooks for exploring course data and degree requirements
- **HTML Subject Mapping**: Extraction and mapping of subject classifications from course catalog HTML
- **User Requirements Management**: Processing and structuring of individual student degree requirements
- **FastAPI Backend**: REST API with PostgreSQL, SQLAlchemy ORM, JWT auth, and eligibility/recommendation services

## Future Ideas

### Planning Algorithms

- **Path to Graduation**: Recommended fastest path to complete degree requirements
- **Short & Long-Term Gap Filling**: Optimal course selection for current term and future planning
- **Multi-Major Optimization**: Tools to maximize double/triple majors or minors with minimal additional coursework
- **Blocker Identification**: Analysis of courses blocking degree completion

### User Experience Features

- **Visual Degree Progress Tracking**: Interactive visualization of completed requirements
- **Schedule Conflict Detection**: Automatic identification and resolution of time conflicts
- **Course Prerequisite Visualization**: Interactive graph of course dependencies
- **Multi-Term Planning**: Tools to plan multiple semesters ahead with term-specific constraints
- **Mobile-Responsive Interface**: Full functionality on mobile devices
- **Real-Time Availability**: Integration with registration systems for seat availability

## Folder Structure

```
VandyVisor/
├── config/                        # Configuration files and mappings
│   └── mappings/                  # Subject, career, component, attribute, and school mappings
├── data/                          # Data storage
│   ├── logs/                      # Application logs
│   ├── processed/                 # Cleaned and structured data
│   │   ├── course_catalog/        # Processed course information
│   │   └── user_requirements/     # Structured degree requirements
│   └── raw/                       # Original scraped data
│       ├── course_catalog/        # Raw course catalog data
│       └── user_requirements/     # Raw requirement files
├── backend/                       # FastAPI backend service
│   └── app/                       # API endpoints, models, services, auth
├── docker/                        # Docker configuration files
├── docs/                          # Project documentation
├── notebooks/                     # Jupyter notebooks for analysis
├── scripts/
│   ├── scraping/                  # Async scraping package (primary)
│   │   ├── cli.py                 # Unified CLI entry point
│   │   ├── config.py              # URLs, constants, mapping re-exports
│   │   ├── http.py                # Async HTTP client with retry + semaphore
│   │   ├── storage.py             # JSON I/O with batch upsert and checkpointing
│   │   ├── sections/              # Current-semester section scraping
│   │   │   ├── discover.py        # Keyword search to find class numbers
│   │   │   ├── parse.py           # Section detail HTML parsing (25+ fields)
│   │   │   └── scrape.py          # Section scraping orchestrator
│   │   └── catalog/               # Historical course catalog scraping
│   │       ├── discover.py        # Subject-based course discovery
│   │       ├── parse.py           # Catalog detail HTML parsing (16+ fields)
│   │       └── scrape.py          # Catalog scraping orchestrator
│   ├── course_scraping/           # Legacy synchronous scrapers
│   ├── mapping_extraction/        # Data mapping utilities
│   └── user_data_processing/      # User requirement processors
└── tests/                         # Unit and integration tests
```

## How to Run

### Prerequisites

- Python 3.11+
- pip package manager

### Installation

1. Clone the repository:

   ```bash
   git clone https://github.com/yourusername/VandyVisor.git
   cd VandyVisor
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

### Scraping

The scraping package supports two distinct pipelines via a unified CLI:

```bash
# Scrape current-semester class sections (enrollment, instructors, meetings)
python -m scripts.scraping sections

# Scrape historical course catalog (descriptions, prerequisites, attributes)
python -m scripts.scraping catalog

# Run both scrapers
python -m scripts.scraping all
```

**Options:**

| Flag | Description | Default |
|------|-------------|---------|
| `-c, --concurrency` | Max concurrent requests | 20 |
| `-b, --batch-size` | Entries per checkpoint write | 500 |
| `-t, --term-code` | Override term code (sections only) | auto |
| `-o, --output-dir` | Output directory | `data` |
| `--discover-only` | Only run the discovery phase | false |
| `--scrape-only` | Only run detail scraping (requires prior discovery) | false |

**Output files** (in `data/`):

| File | Description |
|------|-------------|
| `section_listings.json` | Discovered section class numbers and term codes |
| `sections.json` | Full section data (25+ fields per entry) |
| `catalog_listings.json` | Discovered catalog course IDs |
| `catalog.json` | Full catalog data (16+ fields per entry) |

### Other Scripts

- **Process degree requirements**:

  ```bash
  python scripts/user_data_processing/convert_requirements_to_csv.py
  ```

- **Extract subject mappings**:
  ```bash
  python scripts/mapping_extraction/extract_html_subjects.py
  ```

### Data Analysis

Launch Jupyter notebooks for data exploration:

```bash
jupyter notebook notebooks/
```

## Architecture

### Scraping Pipeline

Both scrapers follow a two-phase **discover + scrape** pattern:

1. **Discovery**: Search the Vanderbilt course system to find all relevant IDs (class numbers or course IDs)
2. **Detail scraping**: Fetch the detail page for each discovered ID and parse the HTML into structured JSON

Key design features:
- 20 concurrent async requests via `aiohttp` with semaphore control
- Exponential backoff retry (up to 2 retries per request)
- Batch checkpoint writes every 500 entries to prevent data loss on crash
- Upsert logic preserving `date_added` timestamps for existing entries
- Mapping translations applied at parse time (school, career, component codes)

### Database

VandyVisor uses a PostgreSQL database with two main data families:

1. **Course Catalog Data** (read-mostly):
   - Subjects, courses, requisites, and attributes
   - Programs, majors, minors, and requirement blocks
   - Precomputed unlock graphs for fast recommendations

2. **User State Data** (write-heavy):
   - Student profiles, completions, and waivers
   - Course plans and preferences
   - Audit results and recommendations

For the complete database schema, see `docs/database_schema.sql`.

### Backend

FastAPI service with:
- SQLAlchemy ORM + PostgreSQL (via Docker Compose)
- JWT authentication with role-based access
- Eligibility, recommendation, and audit services
- See `backend/README.md` for backend-specific documentation

## Version Control

**Version**: 1.1.0-alpha
**Last Updated**: April 2026
**Status**: Active Development

---

Made with love by Kesney
