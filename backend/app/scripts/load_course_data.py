import os
import pandas as pd
import argparse
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.models.base import Base
from app.models import Course, Subject, Term


def load_course_data(csv_path: str, db_url: str):
    """
    Load course data from CSV file into the database.
    
    Args:
        csv_path: Path to the CSV file containing course data
        db_url: Database URL to connect to
    """
    # Create engine and session
    engine = create_engine(db_url)
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    
    try:
        # Load CSV data
        df = pd.read_csv(csv_path)
        print(f"Loaded {len(df)} courses from CSV.")
        
        # Create or get subjects
        subjects = {}
        for _, row in df.iterrows():
            subject_code = row.get('subject_code')
            if subject_code and subject_code not in subjects:
                subject = db.query(Subject).filter(Subject.subject_code == subject_code).first()
                if not subject:
                    subject = Subject(
                        subject_code=subject_code,
                        name=row.get('subject_name', f"Subject {subject_code}"),
                        department=row.get('department'),
                        school=row.get('school')
                    )
                    db.add(subject)
                subjects[subject_code] = subject
        
        db.commit()
        print(f"Created/updated {len(subjects)} subjects.")
        
        # Create or get terms
        terms = {}
        for _, row in df.iterrows():
            term_code = row.get('term_code')
            if term_code and term_code not in terms:
                term = db.query(Term).filter(Term.term_code == term_code).first()
                if not term:
                    term = Term(
                        term_code=term_code,
                        name=row.get('term_name', f"Term {term_code}"),
                        academic_year=row.get('academic_year'),
                        start_date=row.get('start_date'),
                        end_date=row.get('end_date')
                    )
                    db.add(term)
                terms[term_code] = term
        
        db.commit()
        print(f"Created/updated {len(terms)} terms.")
        
        # Create or update courses
        courses_created = 0
        courses_updated = 0
        
        for _, row in df.iterrows():
            course_id = row.get('course_id')
            if not course_id:
                # Generate course ID if not provided
                subject_code = row.get('subject_code', '')
                catalog_number = row.get('catalog_number', '')
                course_id = f"{subject_code}{catalog_number}"
            
            course = db.query(Course).filter(Course.id == course_id).first()
            
            if course:
                # Update existing course
                for key, value in row.items():
                    if hasattr(course, key) and value is not None:
                        setattr(course, key, value)
                courses_updated += 1
            else:
                # Create new course
                course_data = {
                    'id': course_id,
                    'subject_code': row.get('subject_code'),
                    'catalog_number': row.get('catalog_number'),
                    'title': row.get('title'),
                    'description': row.get('description'),
                    'units_earned': row.get('units_earned'),
                    'grading_basis': row.get('grading_basis'),
                    'typically_offered': row.get('typically_offered'),
                    'requisites': row.get('requisites'),
                    'level': row.get('level'),
                    'component': row.get('component')
                }
                
                # Filter out None values
                course_data = {k: v for k, v in course_data.items() if v is not None}
                
                course = Course(**course_data)
                db.add(course)
                courses_created += 1
            
            # Commit in batches to avoid memory issues
            if (courses_created + courses_updated) % 100 == 0:
                db.commit()
        
        # Final commit
        db.commit()
        print(f"Created {courses_created} new courses, updated {courses_updated} existing courses.")
        
    except Exception as e:
        db.rollback()
        print(f"Error loading course data: {e}")
        raise
    finally:
        db.close()


def main():
    parser = argparse.ArgumentParser(description="Load course data from CSV into the database")
    parser.add_argument("csv_path", help="Path to the CSV file containing course data")
    parser.add_argument("--db-url", help="Database URL", default=settings.SQLALCHEMY_DATABASE_URI)
    
    args = parser.parse_args()
    load_course_data(args.csv_path, args.db_url)


if __name__ == "__main__":
    main()
