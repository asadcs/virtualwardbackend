# test_questionnaire_templates.py
from fastapi.testclient import TestClient

from main import app
from db import SessionLocal
from role import Role

client = TestClient(app)

ADMIN = {"name": "Admin Sarah", "email": "admin_qt@gmail.com", "password": "12345678"}

STATE = {"admin": {"id": None, "verify": None, "access": None, "refresh": None}}
ROLE_IDS = {"ADMIN": None}
TEMPLATE_IDS: list[int] = []


# ============================================================
# HELPERS
# ============================================================
def _db():
    return SessionLocal()

def _register_admin():
    r = client.post("/users/register", json={
        "name": ADMIN["name"],
        "email": ADMIN["email"],
        "password": ADMIN["password"],
    })
    assert r.status_code == 200, r.text
    body = r.json()
    STATE["admin"]["id"] = body["user_id"]
    STATE["admin"]["verify"] = body["dev_email_verification_token"]

def _verify_admin():
    r = client.post("/users/verify-email", json={"token": STATE["admin"]["verify"]})
    assert r.status_code == 200, r.text

def _login_admin():
    r = client.post("/users/login", json={"email": ADMIN["email"], "password": ADMIN["password"]})
    assert r.status_code == 200, r.text
    body = r.json()
    STATE["admin"]["access"] = body["access_token"]
    STATE["admin"]["refresh"] = body["refresh_token"]

def _auth_headers_admin():
    return {"Authorization": f"Bearer {STATE['admin']['access']}"}

def _create_role_direct(name: str) -> int:
    db = _db()
    try:
        existing = db.query(Role).filter(Role.name == name).first()
        if existing:
            return existing.id
        role = Role(name=name)
        db.add(role)
        db.commit()
        db.refresh(role)
        return role.id
    finally:
        db.close()

def _assign_admin_role():
    r = client.post("/users/assign-role", json={
        "user_id": STATE["admin"]["id"],
        "role_id": ROLE_IDS["ADMIN"],
    })
    assert r.status_code == 200, r.text


# ============================================================
# BOOTSTRAP ADMIN
# ============================================================
def test_qt_01_bootstrap_admin_user():
    _register_admin()
    _verify_admin()
    _login_admin()

def test_qt_02_make_admin_role_and_assign():
    ROLE_IDS["ADMIN"] = _create_role_direct("ADMIN")
    _assign_admin_role()


# ============================================================
# QUESTIONNAIRE TEMPLATES: create 5 in a loop (recursive-ish)
# ============================================================
def test_qt_03_create_5_templates():
    """
    Creates 5 questionnaire templates:
      - mix of types + statuses
      - each has 5 questions (some choice questions include options)
    """
    templates = [
        {
            "name": "Colorectal Post-Surgery Daily Check",
            "type": "COLORECTAL",
            "status": "ACTIVE",
            "questions": [
                {"order": 1, "text": "Do you have a fever today?", "type": "YES_NO", "required": True, "options": []},
                {"order": 2, "text": "Pain score (0-10)", "type": "SCALE", "required": True, "min_value": 0, "max_value": 10, "options": []},
                {"order": 3, "text": "Any nausea or vomiting?", "type": "YES_NO", "required": True, "options": []},
                {"order": 4, "text": "How is your wound site?", "type": "TEXT", "required": False, "options": []},
                {"order": 5, "text": "Are you able to eat normally?", "type": "YES_NO", "required": True, "options": []},
            ],
        },
        {
            "name": "Post-Surgery Recovery Assessment",
            "type": "GENERAL_SURGERY",
            "status": "ACTIVE",
            "questions": [
                {"order": 1, "text": "Did you walk today?", "type": "YES_NO", "required": True, "options": []},
                {"order": 2, "text": "How many hours did you sleep?", "type": "NUMBER", "required": True, "min_value": 0, "max_value": 24, "options": []},
                {"order": 3, "text": "Appetite level", "type": "SINGLE_CHOICE", "required": True, "options": [
                    {"order": 1, "label": "Poor", "value": "poor"},
                    {"order": 2, "label": "Normal", "value": "normal"},
                    {"order": 3, "label": "Good", "value": "good"},
                ]},
                {"order": 4, "text": "Any dizziness?", "type": "YES_NO", "required": True, "options": []},
                {"order": 5, "text": "Comments", "type": "TEXT", "required": False, "options": []},
            ],
        },
        {
            "name": "Cardiac Monitoring (Draft)",
            "type": "CARDIAC",
            "status": "DRAFT",
            "questions": [
                {"order": 1, "text": "Chest pain today?", "type": "YES_NO", "required": True, "options": []},
                {"order": 2, "text": "Breathlessness level (0-10)", "type": "SCALE", "required": True, "min_value": 0, "max_value": 10, "options": []},
                {"order": 3, "text": "Any palpitations?", "type": "YES_NO", "required": True, "options": []},
                {"order": 4, "text": "Blood pressure (systolic)", "type": "NUMBER", "required": False, "min_value": 50, "max_value": 250, "options": []},
                {"order": 5, "text": "Blood pressure (diastolic)", "type": "NUMBER", "required": False, "min_value": 30, "max_value": 150, "options": []},
            ],
        },
        {
            "name": "Diabetes Daily Check",
            "type": "DIABETES",
            "status": "ACTIVE",
            "questions": [
                {"order": 1, "text": "Fasting glucose (mg/dL)", "type": "NUMBER", "required": True, "min_value": 20, "max_value": 600, "options": []},
                {"order": 2, "text": "Did you take your medication?", "type": "YES_NO", "required": True, "options": []},
                {"order": 3, "text": "Any hypoglycemia symptoms?", "type": "MULTI_CHOICE", "required": False, "options": [
                    {"order": 1, "label": "Sweating", "value": "sweating"},
                    {"order": 2, "label": "Shaking", "value": "shaking"},
                    {"order": 3, "label": "Confusion", "value": "confusion"},
                    {"order": 4, "label": "None", "value": "none"},
                ]},
                {"order": 4, "text": "Diet adherence", "type": "SINGLE_CHOICE", "required": True, "options": [
                    {"order": 1, "label": "Poor", "value": "poor"},
                    {"order": 2, "label": "Fair", "value": "fair"},
                    {"order": 3, "label": "Good", "value": "good"},
                ]},
                {"order": 5, "text": "Notes", "type": "TEXT", "required": False, "options": []},
            ],
        },
        {
            "name": "Orthopedic Post-Op Check (Archived)",
            "type": "ORTHOPEDIC",
            "status": "ARCHIVED",
            "questions": [
                {"order": 1, "text": "Pain score (0-10)", "type": "SCALE", "required": True, "min_value": 0, "max_value": 10, "options": []},
                {"order": 2, "text": "Swelling present?", "type": "YES_NO", "required": True, "options": []},
                {"order": 3, "text": "Mobility today", "type": "SINGLE_CHOICE", "required": True, "options": [
                    {"order": 1, "label": "Bedbound", "value": "bedbound"},
                    {"order": 2, "label": "With assistance", "value": "assisted"},
                    {"order": 3, "label": "Independent", "value": "independent"},
                ]},
                {"order": 4, "text": "Any redness around wound?", "type": "YES_NO", "required": True, "options": []},
                {"order": 5, "text": "Comments", "type": "TEXT", "required": False, "options": []},
            ],
        },
    ]

    TEMPLATE_IDS.clear()

    for t in templates:
        r = client.post("/questionnaire-templates/", json=t, headers=_auth_headers_admin())
        assert r.status_code == 200, r.text
        tid = r.json()["template_id"]
        assert isinstance(tid, int)
        TEMPLATE_IDS.append(tid)

    assert len(TEMPLATE_IDS) == 5


def test_qt_04_list_templates_should_include_5():
    r = client.get("/questionnaire-templates/?skip=0&limit=50", headers=_auth_headers_admin())
    assert r.status_code == 200, r.text
    body = r.json()

    ids = {x["id"] for x in body["items"]}
    for tid in TEMPLATE_IDS:
        assert tid in ids


def test_qt_05_stats_should_reflect_created_templates():
    r = client.get("/questionnaire-templates/stats", headers=_auth_headers_admin())
    assert r.status_code == 200, r.text
    s = r.json()

    # At least these 5 exist (there could be others if DB not reset)
    assert s["total"] >= 5
    assert s["active"] >= 3      # COLORECTAL + GENERAL_SURGERY + DIABETES
    assert s["draft"] >= 1       # CARDIAC draft
    assert s["archived"] >= 1    # ORTHOPEDIC archived
