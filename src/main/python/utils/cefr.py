"""
CEFR (Common European Framework) result display for assessment.
Plan mapping: total score percentage to level + name + description for results page.
Bands: A1 0-16, A2 17-33, B1 34-50, B2 51-67, C1 68-84, C2 85-100.
"""

from typing import Dict, Any, List

# Score percentage bands (inclusive upper bound per level)
# A1: 0-16, A2: 17-33, B1: 34-50, B2: 51-67, C1: 68-84, C2: 85-100
CEFR_BANDS: Dict[str, tuple] = {
    "A1": (0, 16),
    "A2": (17, 33),
    "B1": (34, 50),
    "B2": (51, 67),
    "C1": (68, 84),
    "C2": (85, 100),
}

CEFR_LEVEL_NAMES: Dict[str, str] = {
    "A1": "Beginner",
    "A2": "Elementary",
    "B1": "Intermediate",
    "B2": "Upper Intermediate",
    "C1": "Advanced",
    "C2": "Proficient",
}

CEFR_DESCRIPTIONS: Dict[str, str] = {
    "A1": "Can understand and use very basic phrases for concrete needs.",
    "A2": "Can understand frequently used expressions related to most relevant areas.",
    "B1": "Can deal with most situations likely to arise while travelling or at work.",
    "B2": "Can interact with a degree of fluency and spontaneity with native speakers.",
    "C1": "Can use language flexibly and effectively for social, academic and professional purposes.",
    "C2": "Can understand with ease virtually everything heard or read.",
}


def score_percentage_to_cefr(percentage: int) -> str:
    """Map overall score percentage (0-100) to CEFR level using plan bands."""
    percentage = max(0, min(100, int(percentage)))
    for level, (low, high) in CEFR_BANDS.items():
        if low <= percentage <= high:
            return level
    return "A1"


CEFR_CRUISE_DESCRIPTIONS: Dict[str, str] = {
    "A1": "Can handle very basic greetings and simple requests from guests using memorised phrases.",
    "A2": "Can take simple orders, give basic directions on the ship, and understand routine announcements.",
    "B1": "Can handle most guest interactions, explain services, and resolve common onboard issues independently.",
    "B2": "Can communicate fluently with guests and crew, manage complaints, and participate in team briefings with ease.",
    "C1": "Can lead training sessions, write detailed reports, and handle complex or sensitive guest situations professionally.",
    "C2": "Can perform at native-level fluency across all shipboard contexts, from emergency broadcasts to executive presentations.",
}

CEFR_LEVEL_ORDER: List[str] = ["A1", "A2", "B1", "B2", "C1", "C2"]

CEFR_SCORE_RANGES: Dict[str, str] = {
    "A1": "0 – 16 %",
    "A2": "17 – 33 %",
    "B1": "34 – 50 %",
    "B2": "51 – 67 %",
    "C1": "68 – 84 %",
    "C2": "85 – 100 %",
}


def get_cefr_display(percentage: int) -> Dict[str, Any]:
    """Return CEFR level, name, and description for results page."""
    level = score_percentage_to_cefr(percentage)
    return {
        "cefr_level": level,
        "cefr_name": CEFR_LEVEL_NAMES.get(level, "Beginner"),
        "cefr_description": CEFR_DESCRIPTIONS.get(level, ""),
    }


def get_all_cefr_levels() -> List[Dict[str, str]]:
    """Return ordered list of all CEFR levels with metadata for the results page."""
    return [
        {
            "level": lvl,
            "name": CEFR_LEVEL_NAMES[lvl],
            "description": CEFR_DESCRIPTIONS[lvl],
            "cruise_description": CEFR_CRUISE_DESCRIPTIONS[lvl],
            "score_range": CEFR_SCORE_RANGES[lvl],
        }
        for lvl in CEFR_LEVEL_ORDER
    ]
