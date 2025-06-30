"""
Vanderbilt University course system mappings.

This package contains all the mapping dictionaries used throughout the 
Vanderbilt course scraping system, organized by category for easy reuse.
"""

from .school_mappings import SCHOOL_MAP
from .career_mappings import CAREER_MAP
from .component_mappings import COMPONENT_MAP
from .subject_mappings import SUBJECT_MAP
from .attribute_mappings import ATTRIBUTE_MAP

__all__ = [
    'SCHOOL_MAP',
    'CAREER_MAP', 
    'COMPONENT_MAP',
    'SUBJECT_MAP',
    'ATTRIBUTE_MAP'
]
