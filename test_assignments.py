# test_assignments.py
from datetime import date, timedelta

from fastapi.testclient import TestClient

from main import app
from db import Base, engine, SessionLocal
from role import Role

client = TestClient(app)

# ============================================================
# RESET DB (keeps this file independent)
# ============================================================
def setup_module(module):
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

# ============================================================
# TEST USERS
# ============================================================
ADMIN = {"name": "Admin A", "email": "admin_assign@gmail.com", "password": "12345678"}
PATIENT = {"name": "Patient P", "email": "patient_assign@gmail.com", "password": "password123"}

STATE = {
    "admin": {"id": None, "verify": None, "access": None, "refresh": None},
    "patient": {"id": None, "verify": None, "access": None, "refresh": None},
}

ROLE_IDS = {"ADMIN": None}

TEMPLATE_ID: int | None = None
ASSIGNMENT_ID: int | None = None


# ============================================================
# HELPERS
# ============================================================
def _db():
    return SessionLocal()

def _register(key: str, u: dict):
    r = client.post("/users/register", json={
        "name": u["name"],
        "email": u["email"],
        "password": u["password"],
    })
    assert r.status_code == 200, r.text
    body = r.json()
    STATE[key]["id"] = body["user_id"]
    STATE[key]["verify"] = body["dev_email_verification_token"]

def _verify(key: str):
    r = client.post("/users/verify-email", json={"token": STATE[key]["verify"]})
    assert r.status_code == 200, r.text

def _login(key: str, u: dict):
    r = client.post("/users/login", json={"email": u["email"], "password": u["password"]})
    assert r.status_code == 200, r.text
    body = r.json()
    STATE[key]["access"] = body["access_token"]
    STATE[key]["refresh"] = body["refresh_token"]

def _auth_headers(key: str):
    return {"Authorization": f"Bearer {STATE[key]['access']}"}

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

def _assign_role(user_id: int, role_id: int):
    r = client.post("/users/assign-role", json={"user_id": user_id, "role_id": role_id})
    assert r.status_code == 200, r.text


# ============================================================
# BOOTSTRAP USERS + ADMIN ROLE
# ============================================================
def test_as_01_bootstrap_admin_and_patient():
    _register("admin", ADMIN)
    _register("patient", PATIENT)

    _verify("admin")
    _verify("patient")

    _login("admin", ADMIN)
    _login("patient", PATIENT)

def test_as_02_make_admin_role_and_assign_to_admin():
    ROLE_IDS["ADMIN"] = _create_role_direct("ADMIN")
    _assign_role(STATE["admin"]["id"], ROLE_IDS["ADMIN"])


# ============================================================
# CREATE A PATIENT MEDICAL RECORD (so /assignments can validate patient)
# ============================================================
def test_as_03_register_internal_patient_as_admin():
    """
    Your assignments router validates patient is a "patient" by checking
    PatientMedicalInfo exists. So we must create it.

    We will create an internal patient record for the SAME login patient user
    by calling /patients/register-internal with a different email would create a new user,
    which wouldn't match STATE['patient']['id'].

    Therefore, this test assumes your assignments.py _ensure_patient_exists()
    only requires the user exists (and optionally PatientMedicalInfo).
    If it REQUIRES PatientMedicalInfo, the easiest is:
      - use the patient_id returned from /patients/register-internal as the patient user id.
    """
    # Create a new internal patient to use for assignment
    r = client.post(
        "/patients/register-internal",
        headers=_auth_headers("admin"),
        json={
            "mrn": "MRNASSIGN0001",
            "name": "Internal Assign Patient",
            "age": 44,
            "phone": "123",
            "email": "internal_assign_patient@gmail.com",
            "procedure": "Colorectal Surgery",
            "surgery_date": "2025-01-10",
            "discharge_date": "2025-01-12",
            "notes": "ok",
        },
    )
    assert r.status_code == 200, r.text
    body = r.json()

    # Overwrite STATE["patient"]["id"] so assignment uses a valid patient medical record.
    STATE["patient"]["id"] = body["patient_id"]


# ============================================================
# CREATE AN ACTIVE TEMPLATE AS ADMIN
# ============================================================
def test_as_04_create_one_active_template():
    global TEMPLATE_ID
    payload = {
        "name": "Colorectal Daily Check (Assignment Test)",
        "type": "COLORECTAL",
        "status": "ACTIVE",
        "questions": [
            {"order": 1, "text": "Do you have a fever today?", "type": "YES_NO", "required": True, "options": []},
            {"order": 2, "text": "Pain score (0-10)", "type": "SCALE", "required": True, "min_value": 0, "max_value": 10, "options": []},
        ],
    }
    r = client.post("/questionnaire-templates/", json=payload, headers=_auth_headers("admin"))
    assert r.status_code == 200, r.text
    TEMPLATE_ID = r.json()["template_id"]
    assert isinstance(TEMPLATE_ID, int)


# ============================================================
# ASSIGNMENTS: ADMIN can assign, PATIENT can only view their own
# ============================================================
def test_as_05_patient_cannot_assign_template_403():
    start = date.today()
    end = start + timedelta(days=29)
    r = client.post(
        "/assignments/",
        headers=_auth_headers("patient"),
        json={
            "patient_id": STATE["patient"]["id"],
            "template_id": TEMPLATE_ID,
            "start_date": start.isoformat(),
            "end_date": end.isoformat(),
            "frequency": "DAILY",
        },
    )
    assert r.status_code == 403, r.text


def test_as_06_admin_assigns_template_to_patient_success():
    global ASSIGNMENT_ID
    start = date.today()
    end = start + timedelta(days=29)

    r = client.post(
        "/assignments/",
        headers=_auth_headers("admin"),
        json={
            "patient_id": STATE["patient"]["id"],
            "template_id": TEMPLATE_ID,
            "start_date": start.isoformat(),
            "end_date": end.isoformat(),
            "frequency": "DAILY",
        },
    )
    assert r.status_code == 200, r.text
    ASSIGNMENT_ID = r.json()["assignment_id"]
    assert isinstance(ASSIGNMENT_ID, int)


def test_as_07_admin_lists_assignments_for_patient():
    r = client.get(
        f"/assignments/patient/{STATE['patient']['id']}",
        headers=_auth_headers("admin"),
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["total"] >= 1
    assert any(x["id"] == ASSIGNMENT_ID for x in body["items"])


def test_as_08_patient_lists_my_assignments_only():
    """
    Patient should only see assignments for their own user id.
    This endpoint uses current_user from token, so we need a patient login token
    that matches the assigned patient. Since we used /patients/register-internal
    to create a NEW patient user, we must login as that internal patient.

    If your internal patient password is DEFAULT_PATIENT_PASSWORD ("12345678"),
    use it here.
    """
    # login as the internal patient that was created in test_as_03
    r = client.post("/users/login", json={"email": "internal_assign_patient@gmail.com", "password": "12345678"})
    assert r.status_code == 200, r.text
    internal_access = r.json()["access_token"]

    r = client.get(
        "/assignments/me",
        headers={"Authorization": f"Bearer {internal_access}"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["total"] >= 1
    assert all(x["patient_id"] == STATE["patient"]["id"] for x in body["items"])


def test_as_09_patient_lists_my_assignments_today_only():
    r = client.post("/users/login", json={"email": "internal_assign_patient@gmail.com", "password": "12345678"})
    assert r.status_code == 200, r.text
    internal_access = r.json()["access_token"]

    r = client.get(
        "/assignments/me?today_only=true",
        headers={"Authorization": f"Bearer {internal_access}"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    # since start_date is today, it should be included
    assert any(x["id"] == ASSIGNMENT_ID for x in body["items"])


def test_as_10_admin_deactivates_assignment():
    r = client.post(f"/assignments/{ASSIGNMENT_ID}/deactivate", headers=_auth_headers("admin"))
    assert r.status_code == 200, r.text

    # confirm not listed when active_only=true
    r = client.get(
        f"/assignments/patient/{STATE['patient']['id']}?active_only=true",
        headers=_auth_headers("admin"),
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert all(x["id"] != ASSIGNMENT_ID for x in body["items"])
