"""
Blueprint quotas for grammar question generation per CEFR level.

Counts per level match MODULE_CEFR_DISTRIBUTION['Grammar'] in data.cefr_spec
(A1:2, A2:4, B1:5, B2:5, C1:3, C2:1 → 20 total per department).
"""

from typing import Dict

# grammar_type → grammar_topic → count at that CEFR
GRAMMAR_BLUEPRINT: Dict[str, Dict[str, Dict[str, int]]] = {
    "A1": {
        "Core": {
            "Present Simple": 1,
            "To Be Verb": 1,
        },
        "RoleContext": {},
    },
    "A2": {
        "Core": {
            "Past Simple": 2,
            "Modals Can/Must": 1,
        },
        "RoleContext": {
            "Service Language": 1,
        },
    },
    "B1": {
        "Core": {
            "Present Perfect": 2,
            "Passive Voice": 1,
        },
        "RoleContext": {
            "Service Language": 2,
        },
    },
    "B2": {
        "Core": {
            "Past Perfect": 2,
            "Reported Speech": 1,
        },
        "RoleContext": {
            "Professional Register": 2,
        },
    },
    "C1": {
        "Core": {
            "Obligation": 2,
        },
        "RoleContext": {
            "Formal Procedures": 1,
        },
    },
    "C2": {
        "Core": {
            "Nuanced Modality": 1,
        },
        "RoleContext": {},
    },
}


def grammar_slot_counts_ok() -> bool:
    """Sanity check: blueprint totals match MODULE_CEFR_DISTRIBUTION Grammar."""
    from data.cefr_spec import MODULE_CEFR_DISTRIBUTION

    expected = MODULE_CEFR_DISTRIBUTION["Grammar"]
    for level, exp in expected.items():
        total = 0
        for _gtype, topics in GRAMMAR_BLUEPRINT.get(level, {}).items():
            total += sum(topics.values())
        if total != exp:
            return False
    return True
