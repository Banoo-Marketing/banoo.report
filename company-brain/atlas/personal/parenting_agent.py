"""
parenting_agent.py — Developmental milestone tracker for Diyar and Dario.

Calculates age from birth_date, identifies developmental stage,
recommends weekly activities. Runs weekly.
"""
from __future__ import annotations
import json
import sys
from datetime import date
from pathlib import Path

_HERE = Path(__file__).parent        # atlas/personal/
_ATLAS = _HERE.parent                 # atlas/
_CHIEF = _ATLAS.parent / "chief"

sys.path.insert(0, str(_CHIEF))
sys.path.insert(0, str(_ATLAS))

try:
    from dotenv import load_dotenv
    load_dotenv(_ATLAS.parent.parent / "company-brain" / ".env")
except ImportError:
    pass

import db

_CHILDREN = [
    {"child_name": "Diyar", "birth_date": "2025-04-15"},
    {"child_name": "Dario", "birth_date": "2025-04-15"},
]

# (min_weeks_inclusive, max_weeks_exclusive, stage_name, stage_description)
_STAGES = [
    (0,  4,   "newborn",      "Sleep regulation, rooting reflex, auditory response"),
    (4,  8,   "early_alert",  "Social smiling, cooing, visual tracking begins"),
    (8,  12,  "engaging",     "Tummy time strength, grasping, vocal exchanges"),
    (12, 16,  "interactive",  "Laughing, reaching, head control, object tracking"),
    (16, 24,  "exploring",    "Rolling, sitting with support, babbling"),
    (24, 52,  "mobile",       "Crawling, standing, first words emerging"),
    (52, 999, "toddler",      "Walking, first words, cause-effect play, social awareness"),
]

_ACTIVITIES: dict[str, list[str]] = {
    "newborn":     ["Skin-to-skin contact 20 min/day", "Auditory stimulation with soft voices", "Track moving objects 30cm away", "Gentle massage after bath"],
    "early_alert": ["Tummy time 3x daily for 5 min", "Black-and-white visual cards", "Mimic facial expressions", "Narrate your actions aloud"],
    "engaging":    ["Supervised tummy time 10+ min", "Reaching for hanging toys", "Sensory textures — soft/rough/smooth", "Vocal exchange games (respond to coos)"],
    "interactive": ["Peek-a-boo sessions", "High-contrast picture books", "Assisted sitting with support", "Rolling practice on play mat"],
    "exploring":   ["Rolling practice both directions", "Supported standing at furniture", "Cause-effect toys (press = sound)", "Finger food introduction prep"],
    "mobile":      ["Crawling obstacle course", "Supported walking along furniture", "Simple 2-piece puzzles", "Ball rolling back and forth"],
    "toddler":     ["Walking on different surfaces", "Simple shape sorters", "Naming objects in pictures", "Parallel play with other children"],
}


def calculate_age_weeks(birth_date: str) -> int:
    try:
        bd = date.fromisoformat(birth_date[:10])
        return (date.today() - bd).days // 7
    except (ValueError, TypeError):
        return 0


def get_stage(age_weeks: int) -> dict:
    for min_w, max_w, name, desc in _STAGES:
        if min_w <= age_weeks < max_w:
            return {"name": name, "description": desc, "min_weeks": min_w, "max_weeks": max_w}
    return {"name": "unknown", "description": "Stage not mapped", "min_weeks": 0, "max_weeks": 0}


def recommend_activities(stage: str, age_weeks: int) -> list[str]:
    return _ACTIVITIES.get(stage, ["Responsive play", "Reading together", "Outdoor stimulation"])


def _seed_profiles():
    """Seed child profiles if not present."""
    for child in _CHILDREN:
        if not db.get_child_profile(child["child_name"]):
            db.upsert_child_profile(child)


def run_pipeline() -> dict:
    """Returns triage dict with developmental summaries and activity recommendations."""
    db.init()
    _seed_profiles()

    summaries = []
    exceptions = []

    for child_seed in _CHILDREN:
        name = child_seed["child_name"]
        profile = db.get_child_profile(name) or child_seed
        birth_date = profile.get("birth_date") or child_seed["birth_date"]

        age_weeks = calculate_age_weeks(birth_date)
        stage_info = get_stage(age_weeks)
        stage = stage_info["name"]
        activities = recommend_activities(stage, age_weeks)

        # Update profile in DB
        db.upsert_child_profile({
            "child_name": name,
            "birth_date": birth_date,
            "developmental_stage": stage,
            "current_focus": stage_info["description"],
            "recommended_activities": json.dumps(activities),
        })

        summaries.append(
            f"{name}: {age_weeks}wk ({stage}) — {stage_info['description']}"
        )

    summary = "Parenting update: " + "; ".join(summaries) + ". Activities updated in DB."

    return {
        "agent_name": "parenting",
        "summary": summary,
        "exceptions": exceptions,
        "has_escalation": False,
        "escalation_reason": "",
        "child_summaries": summaries,
    }


def _print_summary():
    db.init()
    _seed_profiles()
    print(f"\n  Parenting Intelligence — {date.today()}\n  {'─'*52}")
    for child_seed in _CHILDREN:
        name = child_seed["child_name"]
        profile = db.get_child_profile(name) or child_seed
        birth_date = profile.get("birth_date") or child_seed["birth_date"]
        age_weeks = calculate_age_weeks(birth_date)
        stage_info = get_stage(age_weeks)
        activities = recommend_activities(stage_info["name"], age_weeks)
        print(f"\n  {name} — {age_weeks} weeks old")
        print(f"  Stage    : {stage_info['name']} — {stage_info['description']}")
        print(f"  Activities this week:")
        for act in activities:
            print(f"    * {act}")


if __name__ == "__main__":
    _print_summary()
