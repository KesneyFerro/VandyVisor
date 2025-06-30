"""
Extract subject mappings from HTML file.

This module parses an HTML file to extract title-value mappings from 
multi-select option containers, commonly used for subject codes and names.
"""

from bs4 import BeautifulSoup
from typing import Dict, Optional
import os


def extract_subject_mappings(html_file_path: str) -> Dict[str, str]:
    """
    Extract title-value mappings from HTML multi-select containers.
    
    Args:
        html_file_path: Path to the HTML file to parse
        
    Returns:
        Dictionary mapping titles to values
        
    Raises:
        FileNotFoundError: If the HTML file doesn't exist
        Exception: If there's an error parsing the HTML
    """
    try:
        with open(html_file_path, 'r', encoding='utf-8') as file:
            soup = BeautifulSoup(file, 'html.parser')
    except FileNotFoundError:
        print(f"Error: File '{html_file_path}' not found")
        return {}
    except Exception as e:
        print(f"Error reading file: {e}")
        return {}

    title_value_map = {}

    # Find all multi-select option containers
    containers = soup.find_all("div", class_="multiSelectOptionContainer")
    
    for container in containers:
        input_tag = container.find("input", class_="multiSelectOption")
        if input_tag:
            title = input_tag.get("title")
            value = input_tag.get("value")
            if title and value:
                title_value_map[title] = value

    return title_value_map


def save_mappings_to_file(mappings: Dict[str, str], output_path: str) -> bool:
    """
    Save the extracted mappings to a Python file in the correct format.
    
    Args:
        mappings: Dictionary of title-value mappings
        output_path: Path to the output Python file
        
    Returns:
        True if successful, False otherwise
    """
    try:
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as file:
            file.write('"""\n')
            file.write('Subject code mappings for Vanderbilt University system.\n\n')
            file.write('This module contains the mapping from full subject/department names to their\n')
            file.write('abbreviated codes used throughout the Vanderbilt course system.\n')
            file.write('"""\n\n')
            
            file.write('SUBJECT_MAP = {\n')
            
            # Sort mappings alphabetically for consistency
            sorted_mappings = sorted(mappings.items())
            
            for i, (title, value) in enumerate(sorted_mappings):
                # Escape single quotes in the title
                escaped_title = title.replace("'", "\\'")
                
                # Add comma for all except the last item
                comma = ',' if i < len(sorted_mappings) - 1 else ''
                
                file.write(f"    '{escaped_title}': '{value}'{comma}\n")
            
            file.write('}\n')
        
        return True
        
    except Exception as e:
        print(f"Error saving mappings to file: {e}")
        return False


def main():
    """Main function to demonstrate usage."""
    html_path = "../../data/raw/course_catalog/subjects.html"
    output_path = "../../config/mappings/subject_mappings.py"
    
    try:
        print("Extracting subject mappings from HTML...")
        mappings = extract_subject_mappings(html_path)
        
        if mappings:
            print(f"Successfully extracted {len(mappings)} mappings")
            
            # Save to Python file
            if save_mappings_to_file(mappings, output_path):
                print(f"Mappings saved to {output_path}")
                
                # Display first few mappings as preview
                print("\nPreview of extracted mappings:")
                for i, (title, value) in enumerate(sorted(mappings.items())):
                    if i < 5:  # Show first 5 mappings
                        print(f"  '{title}': '{value}'")
                    else:
                        print(f"  ... and {len(mappings) - 5} more")
                        break
            else:
                print("Failed to save mappings to file")
        else:
            print("No mappings found or file could not be processed")
            
    except Exception as e:
        print(f"An error occurred: {e}")


if __name__ == "__main__":
    main()
