import os
import json
import argparse
import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.models.base import Base
from app.models import Program, RequirementBlock, RequirementCourse


def load_requirements(json_path: str, db_url: str):
    """
    Load degree requirements from JSON file into the database.
    
    Args:
        json_path: Path to the JSON file containing degree requirements
        db_url: Database URL to connect to
    """
    # Create engine and session
    engine = create_engine(db_url)
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    
    try:
        # Load JSON data
        with open(json_path, 'r') as f:
            data = json.load(f)
        
        print(f"Loaded degree requirements from JSON.")
        
        # Create or update program
        program_data = data.get('program', {})
        program_code = program_data.get('code')
        
        program = db.query(Program).filter(Program.code == program_code).first()
        if program:
            # Update existing program
            for key, value in program_data.items():
                if hasattr(program, key):
                    setattr(program, key, value)
        else:
            # Create new program
            program = Program(
                code=program_code,
                name=program_data.get('name'),
                type=program_data.get('type'),
                department=program_data.get('department'),
                school=program_data.get('school'),
                total_credits=program_data.get('total_credits')
            )
            db.add(program)
        
        db.commit()
        print(f"Created/updated program: {program.name}")
        
        # Process requirement blocks
        blocks = data.get('requirements', [])
        process_requirement_blocks(db, blocks, program.id)
        
        print(f"Successfully loaded degree requirements for {program.name}")
        
    except Exception as e:
        db.rollback()
        print(f"Error loading requirements: {e}")
        raise
    finally:
        db.close()


def process_requirement_blocks(db, blocks, program_id, parent_id=None):
    """Process requirement blocks recursively."""
    for block_data in blocks:
        block = RequirementBlock(
            name=block_data.get('name'),
            description=block_data.get('description'),
            program_id=program_id,
            parent_id=parent_id,
            required_credits=block_data.get('required_credits'),
            required_courses=block_data.get('required_courses'),
            block_type=block_data.get('type', 'standard')
        )
        db.add(block)
        db.flush()  # Get the ID for child relationships
        
        # Process courses in this block
        courses = block_data.get('courses', [])
        for course_data in courses:
            course = RequirementCourse(
                block_id=block.id,
                course_id=course_data.get('course_id'),
                subject_code=course_data.get('subject_code'),
                catalog_number=course_data.get('catalog_number'),
                required=course_data.get('required', True)
            )
            db.add(course)
        
        # Process sub-blocks recursively
        sub_blocks = block_data.get('blocks', [])
        if sub_blocks:
            process_requirement_blocks(db, sub_blocks, program_id, block.id)
    
    db.commit()


def main():
    parser = argparse.ArgumentParser(description="Load degree requirements from JSON into the database")
    parser.add_argument("json_path", help="Path to the JSON file containing degree requirements")
    parser.add_argument("--db-url", help="Database URL", default=settings.SQLALCHEMY_DATABASE_URI)
    
    args = parser.parse_args()
    load_requirements(args.json_path, args.db_url)


if __name__ == "__main__":
    main()
