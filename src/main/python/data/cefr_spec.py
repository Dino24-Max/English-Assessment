"""
CEFR (Common European Framework of Reference) specification for question bank generation.
Levels A1-C2 per Council of Europe / Global English Test. Content and language must match level.
"""

from typing import Any, Dict, List

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

# Sentence length and complexity constraints by CEFR (for content generation)
# max_words: approximate max words per sentence; clauses: typical clause count range
CEFR_SENTENCE_COMPLEXITY: Dict[str, Dict[str, Any]] = {
    "A1": {"max_words": 8, "clauses_min": 1, "clauses_max": 1, "passive_ok": False},
    "A2": {"max_words": 12, "clauses_min": 1, "clauses_max": 2, "passive_ok": False},
    "B1": {"max_words": 18, "clauses_min": 1, "clauses_max": 2, "passive_ok": True},
    "B2": {"max_words": 25, "clauses_min": 2, "clauses_max": 3, "passive_ok": True},
    "C1": {"max_words": 35, "clauses_min": 2, "clauses_max": 4, "passive_ok": True},
    "C2": {"max_words": 45, "clauses_min": 2, "clauses_max": 5, "passive_ok": True},
}

# Module-specific CEFR rules (Council of Europe descriptors)
# Listening: audio script length/complexity
# Reading: passage length, inference required
# Grammar: grammar structures
# Vocabulary: term difficulty
# Speaking: prompt complexity
# TimeNumbers: context wording complexity
CEFR_MODULE_RULES: Dict[str, Dict[str, Dict[str, Any]]] = {
    "Listening": {
        "A1": {"script_sentences": 1, "inference": False, "register": "familiar daily"},
        "A2": {"script_sentences": 1, "inference": False, "register": "direct exchange"},
        "B1": {"script_sentences": 2, "inference": False, "register": "clear standard"},
        "B2": {"script_sentences": 2, "inference": True, "register": "fluent"},
        "C1": {"script_sentences": 3, "inference": True, "register": "professional"},
        "C2": {"script_sentences": 4, "inference": True, "register": "nuanced"},
    },
    "Reading": {
        "A1": {"paragraphs": 1, "sentences": 2, "inference": False},
        "A2": {"paragraphs": 1, "sentences": 3, "inference": False},
        "B1": {"paragraphs": 1, "sentences": 5, "inference": False},
        "B2": {"paragraphs": 1, "sentences": 6, "inference": True},
        "C1": {"paragraphs": 2, "sentences": 8, "inference": True},
        "C2": {"paragraphs": 3, "sentences": 12, "inference": True},
    },
    "Grammar": {"A1": {}, "A2": {}, "B1": {}, "B2": {}, "C1": {}, "C2": {}},  # Use CEFR_GRAMMAR_HINTS
    "Vocabulary": {"A1": {}, "A2": {}, "B1": {}, "B2": {}, "C1": {}, "C2": {}},  # Use CEFR_VOCABULARY_HINTS
    "Speaking": {"A1": {"prompt_words": 8}, "A2": {"prompt_words": 12}, "B1": {"prompt_words": 18}, "B2": {"prompt_words": 25}, "C1": {"prompt_words": 35}, "C2": {"prompt_words": 45}},
    "TimeNumbers": {"A1": {"context_simple": True}, "A2": {}, "B1": {}, "B2": {}, "C1": {}, "C2": {}},
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
