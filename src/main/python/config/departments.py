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

# Map each of 30 canonical departments to scenario key used by generate_question_bank
# Scenario keys: Front Desk, Housekeeping, Food & Beverage, Bar Service, Guest Services,
# Cabin Service, Auxiliary Service, Laundry, Photo, Provisions, Deck Department,
# Engine Department, Security Department, Table Games, Slot Machines, Casino Services
DEPARTMENT_TO_SCENARIO: Dict[str, str] = {
    "AUDIO/VISUAL MEDIA": "Auxiliary Service",
    "AUX SERV": "Auxiliary Service",
    "SPA": "Guest Services",
    "BEVERAGE GUEST SERV": "Bar Service",
    "CASINO": "Table Games",
    "CULINARY ARTS": "Food & Beverage",
    "ENT - TECHNICAL": "Guest Services",
    "ENTERTAINMENT": "Guest Services",
    "F&B MGMT": "Food & Beverage",
    "FLEET FINANCE": "Guest Services",
    "GUEST SERVICES": "Guest Services",
    "GUEST TECHNOLOGY": "Guest Services",
    "HOTEL": "Front Desk",
    "HOUSEKEEPING": "Housekeeping",
    "HUMAN RESOURCES": "Guest Services",
    "INFO TECHNOLOGY": "Guest Services",
    "INFOTAINMENT": "Guest Services",
    "LAUNDRY": "Laundry",
    "MUSICIANS": "Guest Services",
    "ONBOARD MEDIA": "Photo",
    "PHOTO": "Photo",
    "PRODUCTION STAFF": "Guest Services",
    "PROVISIONS": "Provisions",
    "REST. SERVICE": "Food & Beverage",
    "SHORE EXCURS": "Guest Services",
    "YOUTH PROGRAMS": "Guest Services",
    "DECK": "Deck Department",
    "ENGINE": "Engine Department",
    "MEDICAL": "Security Department",
    "SECURITY SERVICES": "Security Department",
}

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
    "Table Games": "CASINO",
    "Slot Machines": "CASINO",
    "Casino Services": "CASINO",
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


def normalize_department(name: str) -> str:
    """Convert legacy/generator name to canonical department name."""
    return LEGACY_TO_CANONICAL.get(name, name)
