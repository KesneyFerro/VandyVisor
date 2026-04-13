# VandyVisor Backend

This is the backend service for VandyVisor, a course planning and scheduling application for Vanderbilt University students.

## Features

- Course catalog browsing and searching
- Study plan management
- Course eligibility checking based on prerequisites
- Course recommendations based on user interests and degree requirements
- Degree audit functionality
- User authentication and authorization

## Tech Stack

- **Framework**: FastAPI
- **ORM**: SQLAlchemy
- **Database**: PostgreSQL
- **Authentication**: JWT-based token authentication

## Getting Started

### Prerequisites

- Python 3.8+
- PostgreSQL
- Poetry (recommended for dependency management)

### Installation

1. Clone the repository:

```bash
git clone https://github.com/your-repo/vandyvisor.git
cd vandyvisor/backend
```

2. Create and activate a conda environment:

```bash
# Create a new conda environment (e.g., named vandyvisor)
conda create -n vandyvisor python=3.8
conda activate vandyvisor
```

3. Install dependencies:

```bash
# Using pip inside the conda environment
pip install -r requirements.txt
```

4. Set up environment variables:

```bash
cp .env.example .env
# Edit .env file with your database credentials and other settings
```

5. Create the database:

```bash
# First create the database in PostgreSQL
createdb vandyvisor

# Then run migrations to create tables
alembic upgrade head
```

### Loading Data

1. Load course data from CSV:

```bash
python -m app.scripts.load_course_data data/processed/course_catalog/vanderbilt_courses.csv
```

2. Load degree requirements:

```bash
python -m app.scripts.load_requirements data/raw/user_requirements/reqs.json
```

### Running the Server

```bash
# Development server with auto-reload
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Production server
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## API Documentation

Once the server is running, you can access:

- Swagger UI documentation: http://localhost:8000/docs
- ReDoc documentation: http://localhost:8000/redoc

## Project Structure

```
app/
│
├── api/                    # API endpoints
│   └── api_v1/
│       ├── endpoints/      # API route handlers
│       └── api.py          # API router
│
├── core/                   # Core functionality
│   ├── auth.py            # Authentication utilities
│   └── config.py          # App configuration
│
├── db/                     # Database
│   └── session.py         # Database session management
│
├── models/                 # SQLAlchemy ORM models
│
├── schemas/                # Pydantic schemas for request/response validation
│
├── services/               # Business logic
│   ├── course_eligibility.py
│   ├── course_recommendations.py
│   └── degree_audit.py
│
├── scripts/                # Data loading scripts
│
└── main.py                # Application entry point
```

## Development

### Running Tests

```bash
pytest
```

### Database Migrations

```bash
# Create a new migration
alembic revision --autogenerate -m "Description of changes"

# Apply migrations
alembic upgrade head

# Revert migrations
alembic downgrade -1
```
