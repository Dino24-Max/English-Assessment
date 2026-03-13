"""
CEFR (Common European Framework of Reference) specification for question bank generation.
Levels A1-C2 per Council of Europe / Global English Test. Content and language must match level.
"""

from typing import Dict, List

# Valid CEFR levels
CEFR_LEVELS: List[str] = ["A1", "A2", "B1", "B2", "C1", "C2"]

# Per-module CEFR distribution for 100 questions per department
# Format: {module_name: {cefr_level: count}}
MODULE_CEFR_DISTRIBUTION: Dict[str, Dict[str, int]] = {
    "Listening": {"A1": 2, "A2": 4, "B1": 5, "B2": 5, "C1": 3, "C2": 1},
    "TimeNumbers": {"A1": 2, "A2": 4, "B1": 5, "B2": 5, "C1": 3, "C2": 1},
    "Grammar": {"A1": 2, "A2": 4, "B1": 5, "B2": 5, "C1": 3, "C2": 1},
    "Vocabulary": {"A1": 2, "A2": 4, "B1": 5, "B2": 5, "C1": 3, "C2": 1},
    "Reading": {"A1": 1, "A2": 2, "B1": 3, "B2": 2, "C1": 2, "C2": 0},
    "Speaking": {"A1": 1, "A2": 2, "B1": 2, "B2": 3, "C1": 2, "C2": 0},
}

# Total per 100 questions
TOTAL_CEFR_PER_100: Dict[str, int] = {
    "A1": 10,
    "A2": 20,
    "B1": 25,
    "B2": 25,
    "C1": 15,
    "C2": 5,
}

# Grammar complexity hints by CEFR (for question generation)
CEFR_GRAMMAR_HINTS: Dict[str, List[str]] = {
    "A1": ["present simple", "basic nouns/verbs", "simple yes/no", "numbers 1-100"],
    "A2": ["past simple", "basic modals (can/must)", "common adjectives", "time expressions"],
    "B1": ["present perfect", "conditionals (type 1)", "comparatives", "relative clauses (who/which)"],
    "B2": ["past perfect", "mixed conditionals", "passive voice", "reported speech"],
    "C1": ["complex conditionals", "nominalization", "cohesive devices", "subjunctive/causative"],
    "C2": ["nuanced modality", "idiomatic structures", "formal register", "complex subordination"],
}

# Vocabulary scope hints by CEFR
CEFR_VOCABULARY_HINTS: Dict[str, List[str]] = {
    "A1": ["basic greetings", "numbers/time", "common objects", "simple actions"],
    "A2": ["routine vocabulary", "shopping/places", "descriptions", "past events"],
    "B1": ["abstract concepts", "opinions/feelings", "work terminology", "cause/effect"],
    "B2": ["specialized terms", "formal language", "collocations", "nuanced adjectives"],
    "C1": ["professional jargon", "idioms", "precise terminology", "academic vocabulary"],
    "C2": ["near-native fluency", "subtle distinctions", "domain expertise", "sophisticated expressions"],
}


def get_cefr_distribution_for_module(module: str) -> Dict[str, int]:
    """Return CEFR count per level for a given module."""
    return MODULE_CEFR_DISTRIBUTION.get(module, {}).copy()


def get_grammar_hints(cefr_level: str) -> List[str]:
    """Return grammar complexity hints for a CEFR level."""
    return CEFR_GRAMMAR_HINTS.get(cefr_level, [])


def get_vocabulary_hints(cefr_level: str) -> List[str]:
    """Return vocabulary scope hints for a CEFR level."""
    return CEFR_VOCABULARY_HINTS.get(cefr_level, [])


def score_percentage_to_cefr(percentage: int) -> str:
    """Map overall score percentage to CEFR level for results display.
    Aligns with Council of Europe descriptors for communicative competence.
    """
    if percentage >= 90:
        return "C2"
    if percentage >= 80:
        return "C1"
    if percentage >= 70:
        return "B2"
    if percentage >= 60:
        return "B1"
    if percentage >= 50:
        return "A2"
    return "A1"
