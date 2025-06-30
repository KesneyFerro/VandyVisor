"""
Extract requirement structure from JSON data.

This module processes student requirement data to extract the hierarchical
structure of requirement groups and their metadata for analysis.
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


def extract_requirement_structure(json_data: List[Dict]) -> List[Dict[str, Any]]:
    """
    Extract requirement structure and metadata from JSON data.
    
    Args:
        json_data: List of requirement group dictionaries
        
    Returns:
        List of dictionaries with requirement structure data
    """
    rows = []

    for requirement_group in json_data:
        requirement_list = requirement_group.get("requirementGroups", [])

        for req_group in requirement_list:
            group_name = req_group.get("name", "Unnamed Requirement Group")
            req_group_number = req_group.get("requirementGroupNumber")
            entry_sequence = req_group.get("entrySequence")
            is_main_requirement = bool(req_group.get("plan"))
            requirements = req_group.get("requirements", [])

            for requirement in requirements:
                requirement_lines = requirement.get("requirementLines", [])
                req_number = requirement.get("requirementNumber")
                req_entry_sequence = requirement.get("entrySequence")

                for line in requirement_lines:
                    # Extract data for each requirement line
                    row_data = {
                        "requirement_group_number": req_group_number,
                        "entry_sequence": entry_sequence,
                        "requirement_number": req_number,
                        "requirement_entry_sequence": req_entry_sequence,
                        "group_name": group_name,
                        "is_main_requirement": is_main_requirement,
                        "line_name": line.get("name"),
                        "description": line.get("description"),
                        "status": line.get("status"),
                        "units_required": line.get("unitsRequired"),
                        "units_used": line.get("unitsUsed"),
                        "units_needed": line.get("unitsNeeded")
                    }
                    rows.append(row_data)

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
        "group_name", "is_main_requirement", "line_name", "description", "status",
        "requirement_group_number", "requirement_number",
        "entry_sequence", "requirement_entry_sequence",
        "units_required", "units_used", "units_needed"
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
    """Main function to extract requirement structure."""
    input_file = "../../data/raw/user_requirements/caroline.json"
    output_file = "../../data/processed/user_requirements/requirement_structure.csv"
    
    print("Extracting requirement structure from JSON data...")
    
    # Load JSON data
    json_data = load_json_data(input_file)
    if json_data is None:
        print("Failed to load JSON data. Exiting.")
        return

    # Extract structure data
    structure_rows = extract_requirement_structure(json_data)
    
    if not structure_rows:
        print("No structure data found. Check input file format.")
        return

    # Save to CSV
    success = save_to_csv(structure_rows, output_file)
    
    if success:
        print("Structure extraction completed successfully.")
    else:
        print("Structure extraction failed.")


if __name__ == "__main__":
    main()
