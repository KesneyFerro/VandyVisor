"""
Convert degree requirements JSON to CSV format.

This module processes degree requirement data from JSON format and converts
it to a structured CSV format for easier analysis and manipulation.
"""

import json
import csv
from typing import Dict, List, Any, Optional


def load_json_data(file_path: str) -> Optional[List[Dict]]:
    """
    Load JSON data from file.
    
    Args:
        file_path: Path to the JSON file
        
    Returns:
        Loaded JSON data or None if error occurs
    """
    try:
        with open(file_path, "r", encoding="utf-8") as file:
            return json.load(file)
    except FileNotFoundError:
        print(f"Error: File '{file_path}' not found")
        return None
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON format in '{file_path}': {e}")
        return None
    except Exception as e:
        print(f"Error reading file '{file_path}': {e}")
        return None


def process_requirement_line(shared_data: Dict[str, Any], line: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Process a single requirement line and return rows for CSV.
    
    Args:
        shared_data: Common data for all courses in this requirement
        line: The requirement line data
        
    Returns:
        List of dictionaries representing CSV rows
    """
    rows = []
    
    # Create base row data combining shared data with line-specific data
    base_row_data = {
        **shared_data,
        "description": line.get("description"),
        "status": line.get("status"),
        "units_required": line.get("unitsRequired"),
        "units_used": line.get("unitsUsed"),
        "units_needed": line.get("unitsNeeded")
    }

    # Process courses used to satisfy this requirement
    courses = line.get("coursesUsedToSatisfy", [])
    
    if courses:
        # Create a row for each course
        for course in courses:
            course_row = {
                **base_row_data,
                "term_taken": course.get("termTaken"),
                "course_id": course.get("courseId"),
                "units_earned": course.get("unitsEarned"),
                "units_taken": course.get("unitsTaken"),
                "long_title": course.get("longTitle"),
                "grade": course.get("grade"),
                "sequence": course.get("sequence"),
                "subject": course.get("subject"),
                "catalog_number": course.get("catalogNumber"),
                "display_name": course.get("displayName")
            }
            rows.append(course_row)
    else:
        # Add a row even if no courses are used to satisfy the requirement
        empty_course_row = {
            **base_row_data,
            "term_taken": None,
            "course_id": None,
            "units_earned": None,
            "units_taken": None,
            "long_title": None,
            "grade": None,
            "sequence": None,
            "subject": None,
            "catalog_number": None,
            "display_name": None
        }
        rows.append(empty_course_row)

    return rows


def convert_requirements_to_csv(json_data: List[Dict]) -> List[Dict[str, Any]]:
    """
    Convert requirement groups from JSON format to CSV rows.
    
    Args:
        json_data: List of requirement group dictionaries
        
    Returns:
        List of dictionaries representing CSV rows
    """
    rows = []

    for requirement_group in json_data:
        requirement_list = requirement_group.get("requirementGroups", [])

        for req_group in requirement_list:
            group_name = req_group.get("name", "Unnamed Requirement Group")
            is_main_requirement = bool(req_group.get("plan"))
            requirements = req_group.get("requirements", [])

            for requirement in requirements:
                requirement_lines = requirement.get("requirementLines", [])
                requirement_name = requirement.get("name")

                # Shared data for all lines in this requirement
                shared_data = {
                    "group_name": group_name,
                    "is_main_requirement": is_main_requirement,
                    "requirement_name": requirement_name
                }

                for line in requirement_lines:
                    line_rows = process_requirement_line(shared_data, line)
                    rows.extend(line_rows)

    return rows


def save_to_csv(data: List[Dict[str, Any]], output_file: str) -> bool:
    """
    Save data to CSV file.
    
    Args:
        data: List of dictionaries to save
        output_file: Output CSV file path
        
    Returns:
        True if successful, False otherwise
    """
    if not data:
        print("Warning: No data to save")
        return False

    # Define CSV column headers
    fieldnames = [
        "group_name", "is_main_requirement", "requirement_name", "description", 
        "status", "units_required", "units_used", "units_needed",
        "term_taken", "course_id", "units_earned", "units_taken", 
        "long_title", "grade", "sequence", "subject",
        "catalog_number", "display_name"
    ]

    try:
        with open(output_file, "w", newline='', encoding="utf-8") as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(data)
        
        print(f"Successfully created CSV file: {output_file}")
        print(f"Total rows written: {len(data)}")
        return True
        
    except Exception as e:
        print(f"Error writing to CSV file '{output_file}': {e}")
        return False


def main():
    """Main function to convert requirements JSON to CSV."""
    input_file = "../../data/raw/user_requirements/reqs.json"
    output_file = "../../data/processed/user_requirements/degree_requirements.csv"
    
    print("Converting degree requirements from JSON to CSV format...")
    
    # Load JSON data
    json_data = load_json_data(input_file)
    if json_data is None:
        print("Failed to load JSON data. Exiting.")
        return

    # Convert to CSV format
    csv_rows = convert_requirements_to_csv(json_data)
    
    if not csv_rows:
        print("No data to convert. Check input file format.")
        return

    # Save to CSV
    success = save_to_csv(csv_rows, output_file)
    
    if success:
        print("Conversion completed successfully.")
    else:
        print("Conversion failed.")


if __name__ == "__main__":
    main()
