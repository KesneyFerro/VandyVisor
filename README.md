# VandyVisor

A modern course planning and scheduling system designed to transform the academic advising experience at Vanderbilt University.

## Purpose

VandyVisor aims to create a more visual and intuitive version of the current advising system. By better organizing course data and degree requirements, this project will provide students with a streamlined way to discover relevant courses and match them to their academic schedules. The goal is to make the schedule planning process significantly easier and more efficient for Vandy students.

## Current Capabilities

- **Course Data Scraping**: Automated extraction of course catalog information from Vandy's academic systems
- **Degree Requirements Processing**: Conversion and analysis of degree requirement data into structured formats
- **Data Analysis**: Jupyter notebooks for exploring course data and degree requirements
- **HTML Subject Mapping**: Extraction and mapping of subject classifications from course catalog HTML
- **User Requirements Management**: Processing and structuring of individual student degree requirements

## Future Ideas

- Interactive course recommendation engine
- Visual degree progress tracking
- Schedule conflict detection and resolution
- Course prerequisite visualization
- Integration with academic calendar and registration systems
- Mobile-responsive web interface
- Real-time course availability tracking

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

## Version Control

**Version**: 1.0.0-alpha  
**Last Updated**: June 29, 2025  
**Status**: Active Development

---

Made with ❤️ by Kesney
