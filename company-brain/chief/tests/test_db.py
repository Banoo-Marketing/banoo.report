"""Tests for db.py — run with: pytest tests/"""
import sys
import os
import tempfile
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))


@pytest.fixture
def tmp_db(tmp_path, monkeypatch):
    """Redirect DB_PATH to a temp file for each test."""
    import db
    monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "test_chief.db"))
    db.init()
    return db


def test_init_creates_tables(tmp_db):
    import sqlite3
    with sqlite3.connect(tmp_db.DB_PATH) as c:
        tables = {r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert {"contacts", "actions", "calendar_events", "briefs", "sync_state"} <= tables


def test_upsert_and_get_contact(tmp_db):
    tmp_db.upsert_contact({
        "email": "test@example.com",
        "name": "Test User",
        "relationship": "Acquaintance",
        "strength": 5.0,
    })
    contacts = tmp_db.get_contacts(limit=10)
    assert len(contacts) == 1
    assert contacts[0]["email"] == "test@example.com"
    assert contacts[0]["name"] == "Test User"


def test_upsert_contact_updates_existing(tmp_db):
    tmp_db.upsert_contact({"email": "update@example.com", "name": "Old Name", "strength": 3.0})
    tmp_db.upsert_contact({"email": "update@example.com", "name": "New Name", "strength": 7.0})
    contacts = tmp_db.get_contacts(limit=10)
    assert len(contacts) == 1
    assert contacts[0]["name"] == "New Name"
    assert contacts[0]["strength"] == 7.0


def test_add_and_get_action(tmp_db):
    tmp_db.add_action({
        "title": "Follow up with client",
        "action_type": "followup",
        "priority": "HIGH",
        "from_email": "client@example.com",
    })
    actions = tmp_db.get_actions(status="OPEN", limit=10)
    assert len(actions) == 1
    assert actions[0]["title"] == "Follow up with client"
    assert actions[0]["priority"] == "HIGH"


def test_get_actions_filters_by_priority(tmp_db):
    tmp_db.add_action({"title": "High pri task", "priority": "HIGH"})
    tmp_db.add_action({"title": "Low pri task", "priority": "LOW"})
    high = tmp_db.get_actions(priority="HIGH", limit=10)
    assert len(high) == 1
    assert high[0]["title"] == "High pri task"


def test_upsert_event(tmp_db):
    tmp_db.upsert_event({
        "event_id": "evt001",
        "title": "Team standup",
        "start_time": "2026-06-01T09:00:00Z",
        "end_time": "2026-06-01T09:15:00Z",
        "attendees": [],
    })
    events = tmp_db.get_upcoming_events(days=365)
    assert any(e["title"] == "Team standup" for e in events)


def test_get_top_contacts_sorted_by_strength(tmp_db):
    tmp_db.upsert_contact({"email": "weak@example.com", "name": "Weak", "strength": 2.0})
    tmp_db.upsert_contact({"email": "strong@example.com", "name": "Strong", "strength": 9.0})
    tmp_db.upsert_contact({"email": "mid@example.com", "name": "Mid", "strength": 5.0})
    top = tmp_db.get_top_contacts(n=3)
    assert top[0]["email"] == "strong@example.com"
    assert top[-1]["email"] == "weak@example.com"


def test_stats_returns_counts(tmp_db):
    tmp_db.upsert_contact({"email": "a@example.com", "strength": 5.0})
    tmp_db.add_action({"title": "Do something", "priority": "MEDIUM"})
    st = tmp_db.stats()
    assert st["contacts"] == 1
    assert st["actions_open"] == 1
    assert st["actions_total"] == 1
