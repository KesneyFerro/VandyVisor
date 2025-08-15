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

- **Course Data Scraping**: Automated extraction of course catalog information from Vanderbilt's academic systems
- **Degree Requirements Processing**: Conversion and analysis of degree requirement data into structured formats
- **Data Analysis**: Jupyter notebooks for exploring course data and degree requirements
- **HTML Subject Mapping**: Extraction and mapping of subject classifications from course catalog HTML
- **User Requirements Management**: Processing and structuring of individual student degree requirements
- **Data Transformation**: Scripts to convert raw scraped data into structured formats suitable for analysis

## Future Ideas

### Database & Backend
- **PostgreSQL Database**: Implementation of a comprehensive database schema for course catalog, user state, and planning rules
- **Advanced Course Recommendations**: Algorithm that suggests courses based on:
  - Prerequisites and degree requirements
  - Unlock value (how many future courses a course enables)
  - Term availability and scheduling conflicts

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
├── config/                    # Configuration files and mappings
│   └── mappings/              # Subject, career, and component mappings
├── data/                      # Data storage and processing
│   ├── logs/                  # Application logs
│   ├── processed/             # Cleaned and structured data
│   │   ├── course_catalog/    # Processed course information
│   │   └── user_requirements/ # Structured degree requirements
│   └── raw/                   # Original scraped data
│       ├── course_catalog/    # Raw course catalog data
│       └── user_requirements/ # Raw requirement files
├── docker/                    # Docker configuration files
├── docs/                      # Project documentation
├── notebooks/                 # Jupyter notebooks for analysis
├── scripts/                   # Data processing and scraping scripts
│   ├── course_scraping/       # Course catalog scraping tools
│   ├── mapping_extraction/    # Data mapping utilities
│   └── user_data_processing/  # User requirement processors
└── tests/                     # Unit and integration tests
```

## How to Run

### Prerequisites

- Python 3.8+
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

### Running the Scripts

- **Scrape course catalog**:

  ```bash
  python scripts/course_scraping/scrape_course_catalog.py
  ```

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

## Planned Implementation

### Database Architecture

VandyVisor will use a PostgreSQL database with two main data families:

1. **Course Catalog Data** (read-mostly):
   - Subjects, courses, requisites, and attributes
   - Programs, majors, minors, and requirement blocks
   - Precomputed unlock graphs for fast recommendations

2. **User State Data** (write-heavy):
   - Student profiles, completions, and waivers
   - Course plans and preferences
   - Audit results and recommendations

Key design features:
- Requisites modeled as logic groups (AND/OR relationships)
- Hierarchical requirement blocks with a JSON rule DSL
- Precomputed course-block match tables for fast filtering
- Unlock graphs to identify high-value courses

### API Structure

The API will be implemented using serverless functions (Cloudflare Workers or Vercel Edge Functions) with endpoints such as:
- `GET /eligible?user=...&term=...`: List courses the user is eligible to take
- `GET /recommendations?user=...`: Get personalized course recommendations
- `POST /plans`: Create a degree plan
- `POST /plan_items`: Add course to a term plan

### Hosting Options

Two main options are being considered:

1. **Neon (Serverless Postgres)**:
   - Serverless HTTP driver from edge functions
   - Scalable read computes as needed

2. **Supabase (Postgres + Auth + RLS)**:
   - Built-in authentication and row-level security
   - Edge functions for serverless compute
   - Integrated database management interface

For the complete database schema and planning algorithms, see the documentation in `docs/database_schema.sql` and related files.

## Version Control

**Version**: 1.0.0-alpha  
**Last Updated**: August 14, 2025  
**Status**: Active Development

---

Made with ❤️ by Kesney
