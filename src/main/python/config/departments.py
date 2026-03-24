"""
Canonical department configuration for the Cruise Employee English Assessment Platform.
Source of truth for all 30 departments - used by admin invitation, question generator, and assessment engine.
"""

from typing import Dict, List, Optional

# Operation keys must match admin_invitation.html departmentMapping
HOTEL_OPERATION = "hotel"
MARINE_OPERATION = "marine"

# All 30 departments: 26 Hotel + 4 Marine
DEPARTMENTS: Dict[str, List[str]] = {
    HOTEL_OPERATION: [
        "AUDIO/VISUAL MEDIA",
        "AUX SERV",
        "BEVERAGE GUEST SERV",
        "CASINO",
        "CULINARY ARTS",
        "ENT - TECHNICAL",
        "ENTERTAINMENT",
        "F&B MGMT",
        "FLEET FINANCE",
        "GUEST SERVICES",
        "GUEST TECHNOLOGY",
        "HOTEL",
        "HOUSEKEEPING",
        "HUMAN RESOURCES",
        "INFO TECHNOLOGY",
        "INFOTAINMENT",
        "LAUNDRY",
        "MUSICIANS",
        "ONBOARD MEDIA",
        "PHOTO",
        "PRODUCTION STAFF",
        "PROVISIONS",
        "REST. SERVICE",
        "SHORE EXCURS",
        "SPA",
        "YOUTH PROGRAMS",
    ],
    MARINE_OPERATION: [
        "DECK",
        "ENGINE",
        "MEDICAL",
        "SECURITY SERVICES",
    ],
}

# Flat list of all department names
ALL_DEPARTMENTS: List[str] = DEPARTMENTS[HOTEL_OPERATION] + DEPARTMENTS[MARINE_OPERATION]

# Department count
DEPARTMENT_COUNT: int = len(ALL_DEPARTMENTS)

# Plan alias: single source of truth for 30 departments (26 hotel + 4 marine)
DEPARTMENT_MAPPING: Dict[str, List[str]] = DEPARTMENTS

# Map each of 30 canonical departments to content pool key for scenario lookup.
# Every department has an explicit mapping—no generic fallback.
# Content pools: department-appropriate scenarios (e.g., DECK→deck content, ENGINE→engine content)
DEPARTMENT_TO_CONTENT_POOL: Dict[str, str] = {
    "AUDIO/VISUAL MEDIA": "Audio Visual Media",
    "AUX SERV": "Auxiliary Service",
    "SPA": "Spa & Wellness",
    "BEVERAGE GUEST SERV": "Bar Service",
    "CASINO": "Table Games",
    "CULINARY ARTS": "Food & Beverage",
    "ENT - TECHNICAL": "Entertainment Technical",
    "ENTERTAINMENT": "Entertainment",
    "F&B MGMT": "Food & Beverage",
    "FLEET FINANCE": "Fleet Finance",
    "GUEST SERVICES": "Guest Services",
    "GUEST TECHNOLOGY": "Guest Technology",
    "HOTEL": "Front Desk",
    "HOUSEKEEPING": "Housekeeping",
    "HUMAN RESOURCES": "Human Resources",
    "INFO TECHNOLOGY": "Info Technology",
    "INFOTAINMENT": "Infotainment",
    "LAUNDRY": "Laundry",
    "MUSICIANS": "Musicians",
    "ONBOARD MEDIA": "Onboard Media",
    "PHOTO": "Photo",
    "PRODUCTION STAFF": "Production Staff",
    "PROVISIONS": "Provisions",
    "REST. SERVICE": "Food & Beverage",
    "SHORE EXCURS": "Shore Excursions",
    "YOUTH PROGRAMS": "Youth Programs",
    "DECK": "Deck Department",
    "ENGINE": "Engine Department",
    "MEDICAL": "Medical Department",
    "SECURITY SERVICES": "Security Department",
}

# Backward compatibility
DEPARTMENT_TO_SCENARIO = DEPARTMENT_TO_CONTENT_POOL

# Mapping from legacy/generator display names to canonical department names
# Used when migrating from old question bank keys to new 30-department structure
LEGACY_TO_CANONICAL: Dict[str, str] = {
    "Front Desk": "GUEST SERVICES",
    "Housekeeping": "HOUSEKEEPING",
    "Food & Beverage": "REST. SERVICE",
    "Bar Service": "BEVERAGE GUEST SERV",
    "Guest Services": "GUEST SERVICES",
    "Cabin Service": "HOUSEKEEPING",
    "Auxiliary Service": "AUX SERV",
    "Laundry": "LAUNDRY",
    "Photo": "PHOTO",
    "Provisions": "PROVISIONS",
    "Deck Department": "DECK",
    "Engine Department": "ENGINE",
    "Security Department": "SECURITY SERVICES",
    "Medical Department": "MEDICAL",
    "Table Games": "CASINO",
    "Slot Machines": "CASINO",
    "Casino Services": "CASINO",
    "Human Resource": "HUMAN RESOURCES",
    "Human Resources": "HUMAN RESOURCES",
    "Information Technology": "INFO TECHNOLOGY",
    "Information technology": "INFO TECHNOLOGY",
    "IT": "INFO TECHNOLOGY",
    "Info Tech": "INFO TECHNOLOGY",
    "Info Techology": "INFO TECHNOLOGY",
    "Guest Technology": "GUEST TECHNOLOGY",
}


def get_departments_by_operation(operation: str) -> List[str]:
    """Return departments for a given operation (hotel, marine)."""
    return DEPARTMENTS.get(operation, [])


def get_operation_for_department(department: str) -> Optional[str]:
    """Return operation (hotel/marine) for a given department."""
    for op, depts in DEPARTMENTS.items():
        if department in depts:
            return op
    return None


def normalize_department(name: Optional[str]) -> str:
    """Convert legacy/generator name to canonical department name. Already canonical names are returned as-is."""
    if not name or not str(name).strip():
        return ""
    name = str(name).strip()
    if name in ALL_DEPARTMENTS:
        return name
    return LEGACY_TO_CANONICAL.get(name, name)
