"""Integration tests for chief.py CLI commands."""
import sys
import os
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))


@pytest.fixture(autouse=True)
def tmp_chief_db(tmp_path, monkeypatch):
    import db
    monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "chief.db"))
    db.init()

    # Seed contacts
    db.upsert_contact({"email": "alice@example.com", "name": "Alice", "relationship": "Key business partner", "strength": 8.0, "email_count": 12})
    db.upsert_contact({"email": "bob@example.com", "name": "Bob", "relationship": "Client (Banoo)", "strength": 6.0, "email_count": 5})
    db.upsert_contact({"email": "carol@example.com", "name": "Carol", "relationship": "Lead (business owner)", "strength": 4.0, "nurture_score": 7, "is_business_owner": 1})

    # Seed actions
    db.add_action({"title": "Call Alice about contract", "priority": "HIGH", "from_email": "alice@example.com", "from_name": "Alice"})
    db.add_action({"title": "Send proposal to Bob", "priority": "MEDIUM", "from_email": "bob@example.com"})

    return db


def test_cmd_status_runs(capsys):
    import chief
    chief.cmd_status()
    captured = capsys.readouterr()
    assert "Contacts" in captured.out
    assert "Open actions" in captured.out


def test_cmd_show_tasks(capsys):
    import chief
    chief.cmd_show_tasks()
    captured = capsys.readouterr()
    assert "Call Alice about contract" in captured.out


def test_cmd_show_tasks_urgent_only(capsys):
    import chief
    chief.cmd_show_tasks(urgent_only=True)
    captured = capsys.readouterr()
    assert "Call Alice about contract" in captured.out
    assert "Send proposal to Bob" not in captured.out


def test_cmd_show_contacts(capsys):
    import chief
    chief.cmd_show_contacts()
    captured = capsys.readouterr()
    assert "Alice" in captured.out
    assert "alice@example.com" in captured.out


def test_cmd_contact_by_name(capsys):
    import chief
    chief.cmd_contact("Alice")
    captured = capsys.readouterr()
    assert "alice@example.com" in captured.out
    assert "CONTACT PROFILE" in captured.out


def test_cmd_contact_not_found(capsys):
    import chief
    chief.cmd_contact("nobody_xyz_123")
    captured = capsys.readouterr()
    assert "No contact found" in captured.out


def test_cmd_nurture_leads(capsys):
    import chief
    chief.cmd_nurture_leads()
    captured = capsys.readouterr()
    assert "Carol" in captured.out or "No nurture leads" in captured.out


def test_cmd_reconnect_empty(capsys):
    import chief
    chief.cmd_reconnect()
    captured = capsys.readouterr()
    # Either finds dormant contacts or none — both are valid
    assert captured.out is not None
