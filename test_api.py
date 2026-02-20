# # # from fastapi.testclient import TestClient
# # # from main import app
# # # from db import Base, engine

# # # client = TestClient(app)

# # # # -------------------------
# # # # RESET DB ONCE
# # # # -------------------------
# # # def setup_module(module):
# # #     Base.metadata.drop_all(bind=engine)
# # #     Base.metadata.create_all(bind=engine)

# # # # -------------------------
# # # # GLOBAL TEST STATE
# # # # -------------------------
# # # USER_EMAIL = "testuser@example.com"
# # # USER_PASSWORD = "TestPassword123"
# # # NEW_PASSWORD = "NewPassword123"

# # # access_token = None
# # # refresh_token = None
# # # verify_token = None
# # # reset_token = None
# # # user_id = None

# # # # -------------------------
# # # # 1️⃣ Register User
# # # # -------------------------
# # # def test_register_user():
# # #     global verify_token, user_id

# # #     res = client.post("/users/register", json={
# # #         "name": "Test User",
# # #         "email": USER_EMAIL,
# # #         "password": USER_PASSWORD
# # #     })

# # #     assert res.status_code == 200
# # #     body = res.json()

# # #     verify_token = body["dev_email_verification_token"]
# # #     user_id = body["user_id"]

# # # # -------------------------
# # # # 2️⃣ Verify Email
# # # # -------------------------
# # # def test_verify_email():
# # #     res = client.post("/users/verify-email", json={
# # #         "token": verify_token
# # #     })

# # #     assert res.status_code == 200

# # # # -------------------------
# # # # 3️⃣ Login
# # # # -------------------------
# # # def test_login():
# # #     global access_token, refresh_token

# # #     res = client.post("/users/login", json={
# # #         "email": USER_EMAIL,
# # #         "password": USER_PASSWORD
# # #     })

# # #     assert res.status_code == 200
# # #     body = res.json()

# # #     access_token = body["access_token"]
# # #     refresh_token = body["refresh_token"]

# # # # -------------------------
# # # # 4️⃣ Get Current User
# # # # -------------------------
# # # def test_me():
# # #     res = client.get(
# # #         "/users/me",
# # #         headers={"Authorization": f"Bearer {access_token}"}
# # #     )

# # #     assert res.status_code == 200
# # #     assert res.json()["email"] == USER_EMAIL

# # # # -------------------------
# # # # 5️⃣ Refresh Token
# # # # -------------------------
# # # def test_refresh_token():
# # #     global access_token, refresh_token

# # #     res = client.post("/users/refresh", json={
# # #         "refresh_token": refresh_token
# # #     })

# # #     assert res.status_code == 200
# # #     body = res.json()

# # #     access_token = body["access_token"]
# # #     refresh_token = body["refresh_token"]

# # # # -------------------------
# # # # 6️⃣ Change Password
# # # # -------------------------
# # # def test_change_password():
# # #     res = client.post(
# # #         "/users/change-password",
# # #         json={
# # #             "current_password": USER_PASSWORD,
# # #             "new_password": NEW_PASSWORD
# # #         },
# # #         headers={"Authorization": f"Bearer {access_token}"}
# # #     )

# # #     assert res.status_code == 200

# # # # -------------------------
# # # # 7️⃣ Login with New Password
# # # # -------------------------
# # # def test_login_with_new_password():
# # #     res = client.post("/users/login", json={
# # #         "email": USER_EMAIL,
# # #         "password": NEW_PASSWORD
# # #     })

# # #     assert res.status_code == 200

# # # # -------------------------
# # # # 8️⃣ Request Password Reset
# # # # -------------------------
# # # def test_request_password_reset():
# # #     global reset_token

# # #     res = client.post("/users/request-password-reset", json={
# # #         "email": USER_EMAIL
# # #     })

# # #     assert res.status_code == 200
# # #     reset_token = res.json()["dev_reset_token"]

# # # # -------------------------
# # # # 9️⃣ Reset Password
# # # # -------------------------
# # # def test_reset_password():
# # #     res = client.post("/users/reset-password", json={
# # #         "reset_token": reset_token,
# # #         "new_password": USER_PASSWORD
# # #     })

# # #     assert res.status_code == 200

# # # # -------------------------
# # # # 🔟 Logout
# # # # -------------------------
# # # def test_logout():
# # #     res = client.post("/users/logout", json={
# # #         "refresh_token": refresh_token
# # #     })

# # #     assert res.status_code == 200


# # from fastapi.testclient import TestClient

# # from main import app
# # from db import Base, engine, SessionLocal

# # from role import Role
# # from auth import AuditLog

# # client = TestClient(app)

# # # ============================================================
# # # RESET DB (DELETES ALL PREVIOUS TEST DATA)
# # # ============================================================
# # def setup_module(module):
# #     Base.metadata.drop_all(bind=engine)
# #     Base.metadata.create_all(bind=engine)

# # # ============================================================
# # # TEST USERS (from WhatsApp snapshot)
# # # ============================================================
# # PATIENT = {"name": "Patient", "email": "patient2@gmail.com", "password": "password123"}
# # ADMIN   = {"name": "Admin",   "email": "admin@virtualward.com", "password": "Admin@123"}
# # DOCTOR  = {"name": "Doctor",  "email": "miangali927@gmail.com", "password": "Ahmed3772"}

# # STATE = {
# #     "patient": {"id": None, "verify": None, "access": None, "refresh": None},
# #     "admin":   {"id": None, "verify": None, "access": None, "refresh": None},
# #     "doctor":  {"id": None, "verify": None, "access": None, "refresh": None},
# # }

# # ROLE_IDS = {"ADMIN": None, "DOCTOR": None, "PATIENT": None}


# # # ============================================================
# # # HELPERS
# # # ============================================================
# # def _db():
# #     return SessionLocal()

# # def _register(key: str, u: dict):
# #     r = client.post("/users/register", json={
# #         "name": u["name"],
# #         "email": u["email"],
# #         "password": u["password"],
# #     })
# #     assert r.status_code == 200
# #     body = r.json()
# #     STATE[key]["id"] = body["user_id"]
# #     STATE[key]["verify"] = body["dev_email_verification_token"]

# # def _verify(key: str):
# #     r = client.post("/users/verify-email", json={"token": STATE[key]["verify"]})
# #     assert r.status_code == 200

# # def _login(key: str, u: dict, password_override: str | None = None):
# #     r = client.post("/users/login", json={
# #         "email": u["email"],
# #         "password": password_override or u["password"],
# #     })
# #     return r

# # def _login_ok(key: str, u: dict):
# #     r = _login(key, u)
# #     assert r.status_code == 200
# #     body = r.json()
# #     STATE[key]["access"] = body["access_token"]
# #     STATE[key]["refresh"] = body["refresh_token"]

# # def _auth_headers(key: str):
# #     return {"Authorization": f"Bearer {STATE[key]['access']}"}

# # def _create_role_direct(name: str) -> int:
# #     db = _db()
# #     try:
# #         existing = db.query(Role).filter(Role.name == name).first()
# #         if existing:
# #             return existing.id
# #         role = Role(name=name)
# #         db.add(role)
# #         db.commit()
# #         db.refresh(role)
# #         return role.id
# #     finally:
# #         db.close()


# # # ============================================================
# # # POSITIVE FLOW: USERS
# # # ============================================================
# # def test_01_register_three_users():
# #     _register("patient", PATIENT)
# #     _register("admin", ADMIN)
# #     _register("doctor", DOCTOR)

# # def test_02_register_duplicate_email_returns_400():
# #     r = client.post("/users/register", json={
# #         "name": "Dup",
# #         "email": PATIENT["email"],
# #         "password": "password123",
# #     })
# #     assert r.status_code == 400

# # def test_03_verify_invalid_token_returns_400():
# #     r = client.post("/users/verify-email", json={"token": "invalid-token"})
# #     assert r.status_code == 400

# # def test_04_verify_all_users():
# #     _verify("patient")
# #     _verify("admin")
# #     _verify("doctor")

# # def test_05_login_wrong_password_returns_401():
# #     r = _login("patient", PATIENT, password_override="wrong-pass")
# #     assert r.status_code == 401

# # def test_06_login_all_users():
# #     _login_ok("patient", PATIENT)
# #     _login_ok("admin", ADMIN)
# #     _login_ok("doctor", DOCTOR)

# # def test_07_me_works_for_each_user():
# #     for key, u in [("patient", PATIENT), ("admin", ADMIN), ("doctor", DOCTOR)]:
# #         r = client.get("/users/me", headers=_auth_headers(key))
# #         assert r.status_code == 200
# #         assert r.json()["email"] == u["email"]


# # # ============================================================
# # # ROLES BOOTSTRAP (create roles + assign ADMIN role)
# # # ============================================================
# # def test_08_create_roles_in_db():
# #     ROLE_IDS["ADMIN"] = _create_role_direct("ADMIN")
# #     ROLE_IDS["DOCTOR"] = _create_role_direct("DOCTOR")
# #     ROLE_IDS["PATIENT"] = _create_role_direct("PATIENT")

# # def test_09_assign_roles_to_users():
# #     # admin gets ADMIN
# #     r = client.post("/users/assign-role", json={
# #         "user_id": STATE["admin"]["id"],
# #         "role_id": ROLE_IDS["ADMIN"],
# #     })
# #     assert r.status_code == 200

# #     # doctor gets DOCTOR
# #     r = client.post("/users/assign-role", json={
# #         "user_id": STATE["doctor"]["id"],
# #         "role_id": ROLE_IDS["DOCTOR"],
# #     })
# #     assert r.status_code == 200

# #     # patient gets PATIENT
# #     r = client.post("/users/assign-role", json={
# #         "user_id": STATE["patient"]["id"],
# #         "role_id": ROLE_IDS["PATIENT"],
# #     })
# #     assert r.status_code == 200

# # def test_10_remove_role_works():
# #     # remove PATIENT role from patient
# #     r = client.post("/users/remove-role", json={
# #         "user_id": STATE["patient"]["id"],
# #         "role_id": ROLE_IDS["PATIENT"],
# #     })
# #     assert r.status_code == 200

# #     # confirm removed
# #     r = client.get("/users/me", headers=_auth_headers("patient"))
# #     assert r.status_code == 200
# #     assert "PATIENT" not in r.json()["roles"]

# #     # add back (so later role counts work)
# #     r = client.post("/users/assign-role", json={
# #         "user_id": STATE["patient"]["id"],
# #         "role_id": ROLE_IDS["PATIENT"],
# #     })
# #     assert r.status_code == 200


# # # ============================================================
# # # ROLE API NEGATIVE: create role without admin => 403
# # # ============================================================
# # def test_11_roles_create_without_admin_returns_403():
# #     r = client.post("/roles/", json={"name": "NURSE"}, headers=_auth_headers("patient"))
# #     assert r.status_code == 403


# # # ============================================================
# # # ROLE API CRUD (admin only)
# # # ============================================================
# # def test_12_roles_crud_as_admin():
# #     headers = _auth_headers("admin")

# #     # create
# #     r = client.post("/roles/", json={"name": "NURSE"}, headers=headers)
# #     assert r.status_code == 200
# #     role_id = r.json()["role_id"]

# #     # list
# #     r = client.get("/roles/")
# #     assert r.status_code == 200
# #     assert any(x["name"] == "NURSE" for x in r.json()["items"])

# #     # get
# #     r = client.get(f"/roles/{role_id}")
# #     assert r.status_code == 200
# #     assert r.json()["name"] == "NURSE"

# #     # update
# #     r = client.put(f"/roles/{role_id}", json={"name": "NURSE_UPDATED"}, headers=headers)
# #     assert r.status_code == 200

# #     # confirm update
# #     r = client.get(f"/roles/{role_id}")
# #     assert r.status_code == 200
# #     assert r.json()["name"] == "NURSE_UPDATED"

# #     # delete
# #     r = client.delete(f"/roles/{role_id}", headers=headers)
# #     assert r.status_code == 200

# #     # confirm delete
# #     r = client.get(f"/roles/{role_id}")
# #     assert r.status_code == 404


# # # ============================================================
# # # AUTH NEGATIVE CASES
# # # ============================================================
# # def test_13_refresh_with_invalid_token_returns_401():
# #     r = client.post("/users/refresh", json={"refresh_token": "invalid-refresh-token"})
# #     assert r.status_code == 401

# # def test_14_change_password_wrong_current_returns_400():
# #     r = client.post(
# #         "/users/change-password",
# #         json={"current_password": "wrong", "new_password": "NewPass123"},
# #         headers=_auth_headers("patient"),
# #     )
# #     assert r.status_code == 400

# # def test_15_reset_password_invalid_token_returns_400():
# #     r = client.post("/users/reset-password", json={"reset_token": "bad-token", "new_password": "NewPass123"})
# #     assert r.status_code == 400


# # # ============================================================
# # # AUTH POSITIVE CASES
# # # ============================================================
# # def test_16_refresh_token_success():
# #     r = client.post("/users/refresh", json={"refresh_token": STATE["patient"]["refresh"]})
# #     assert r.status_code == 200
# #     body = r.json()
# #     assert "access_token" in body and "refresh_token" in body
# #     STATE["patient"]["access"] = body["access_token"]
# #     STATE["patient"]["refresh"] = body["refresh_token"]

# # def test_17_request_password_reset_success():
# #     r = client.post("/users/request-password-reset", json={"email": PATIENT["email"]})
# #     assert r.status_code == 200
# #     assert "dev_reset_token" in r.json()
# #     STATE["patient"]["reset_token"] = r.json()["dev_reset_token"]

# # def test_18_reset_password_success():
# #     r = client.post("/users/reset-password", json={
# #         "reset_token": STATE["patient"]["reset_token"],
# #         "new_password": "password123",  # same as original is OK for test
# #     })
# #     assert r.status_code == 200

# # def test_19_logout_success():
# #     r = client.post("/users/logout", json={"refresh_token": STATE["patient"]["refresh"]})
# #     assert r.status_code == 200


# # # ============================================================
# # # AUDIT LOG TABLE CHECK
# # # ============================================================
# # def test_20_audit_logs_exist():
# #     db = _db()
# #     try:
# #         assert db.query(AuditLog).count() > 0
# #     finally:
# #         db.close()

# from fastapi.testclient import TestClient

# from main import app
# from db import Base, engine, SessionLocal

# from role import Role
# from auth import AuditLog

# # NEW: import patient model for DB assertions (optional but useful)
# from patients import PatientMedicalInfo

# client = TestClient(app)

# # ============================================================
# # RESET DB (DELETES ALL PREVIOUS TEST DATA)
# # ============================================================
# def setup_module(module):
#     Base.metadata.drop_all(bind=engine)
#     Base.metadata.create_all(bind=engine)

# # ============================================================
# # TEST USERS
# # ============================================================
# PATIENT = {"name": "Patient", "email": "patient2@gmail.com", "password": "password123"}
# ADMIN   = {"name": "Admin",   "email": "deasad2019@gmail.com", "password": "12345678"}
# DOCTOR  = {"name": "Doctor",  "email": "miangali927@gmail.com", "password": "Ahmed3772"}

# STATE = {
#     "patient": {"id": None, "verify": None, "access": None, "refresh": None},
#     "admin":   {"id": None, "verify": None, "access": None, "refresh": None},
#     "doctor":  {"id": None, "verify": None, "access": None, "refresh": None},
# }

# ROLE_IDS = {"ADMIN": None, "DOCTOR": None, "PATIENT": None}


# # ============================================================
# # HELPERS
# # ============================================================
# def _db():
#     return SessionLocal()

# def _register(key: str, u: dict):
#     r = client.post("/users/register", json={
#         "name": u["name"],
#         "email": u["email"],
#         "password": u["password"],
#     })
#     assert r.status_code == 200
#     body = r.json()
#     STATE[key]["id"] = body["user_id"]
#     STATE[key]["verify"] = body["dev_email_verification_token"]

# def _verify(key: str):
#     r = client.post("/users/verify-email", json={"token": STATE[key]["verify"]})
#     assert r.status_code == 200

# def _login(key: str, u: dict, password_override: str | None = None):
#     r = client.post("/users/login", json={
#         "email": u["email"],
#         "password": password_override or u["password"],
#     })
#     return r

# def _login_ok(key: str, u: dict):
#     r = _login(key, u)
#     assert r.status_code == 200
#     body = r.json()
#     STATE[key]["access"] = body["access_token"]
#     STATE[key]["refresh"] = body["refresh_token"]

# def _auth_headers(key: str):
#     return {"Authorization": f"Bearer {STATE[key]['access']}"}

# def _create_role_direct(name: str) -> int:
#     db = _db()
#     try:
#         existing = db.query(Role).filter(Role.name == name).first()
#         if existing:
#             return existing.id
#         role = Role(name=name)
#         db.add(role)
#         db.commit()
#         db.refresh(role)
#         return role.id
#     finally:
#         db.close()


# # ============================================================
# # POSITIVE FLOW: USERS
# # ============================================================
# def test_01_register_three_users():
#     _register("patient", PATIENT)
#     _register("admin", ADMIN)
#     _register("doctor", DOCTOR)

# def test_02_register_duplicate_email_returns_400():
#     r = client.post("/users/register", json={
#         "name": "Dup",
#         "email": PATIENT["email"],
#         "password": "password123",
#     })
#     assert r.status_code == 400

# def test_03_verify_invalid_token_returns_400():
#     r = client.post("/users/verify-email", json={"token": "invalid-token"})
#     assert r.status_code == 400

# def test_04_verify_all_users():
#     _verify("patient")
#     _verify("admin")
#     _verify("doctor")

# def test_05_login_wrong_password_returns_401():
#     r = _login("patient", PATIENT, password_override="wrong-pass")
#     assert r.status_code == 401

# def test_06_login_all_users():
#     _login_ok("patient", PATIENT)
#     _login_ok("admin", ADMIN)
#     _login_ok("doctor", DOCTOR)

# def test_07_me_works_for_each_user():
#     for key, u in [("patient", PATIENT), ("admin", ADMIN), ("doctor", DOCTOR)]:
#         r = client.get("/users/me", headers=_auth_headers(key))
#         assert r.status_code == 200
#         assert r.json()["email"] == u["email"]


# # ============================================================
# # ROLES BOOTSTRAP (create roles + assign roles)
# # ============================================================
# def test_08_create_roles_in_db():
#     ROLE_IDS["ADMIN"] = _create_role_direct("ADMIN")
#     ROLE_IDS["DOCTOR"] = _create_role_direct("DOCTOR")
#     ROLE_IDS["PATIENT"] = _create_role_direct("PATIENT")

# def test_09_assign_roles_to_users():
#     # admin gets ADMIN
#     r = client.post("/users/assign-role", json={
#         "user_id": STATE["admin"]["id"],
#         "role_id": ROLE_IDS["ADMIN"],
#     })
#     assert r.status_code == 200

#     # doctor gets DOCTOR
#     r = client.post("/users/assign-role", json={
#         "user_id": STATE["doctor"]["id"],
#         "role_id": ROLE_IDS["DOCTOR"],
#     })
#     assert r.status_code == 200

#     # patient gets PATIENT
#     r = client.post("/users/assign-role", json={
#         "user_id": STATE["patient"]["id"],
#         "role_id": ROLE_IDS["PATIENT"],
#     })
#     assert r.status_code == 200

# def test_10_remove_role_works():
#     # remove PATIENT role from patient
#     r = client.post("/users/remove-role", json={
#         "user_id": STATE["patient"]["id"],
#         "role_id": ROLE_IDS["PATIENT"],
#     })
#     assert r.status_code == 200

#     # confirm removed
#     r = client.get("/users/me", headers=_auth_headers("patient"))
#     assert r.status_code == 200
#     assert "PATIENT" not in r.json()["roles"]

#     # add back (so later role counts work)
#     r = client.post("/users/assign-role", json={
#         "user_id": STATE["patient"]["id"],
#         "role_id": ROLE_IDS["PATIENT"],
#     })
#     assert r.status_code == 200


# # ============================================================
# # PATIENTS: /patients/register-internal
# # ============================================================
# def test_11_register_internal_patient_requires_auth_401():
#     r = client.post("/patients/register-internal", json={
#         "mrn": "MRN0001",
#         "name": "Internal One",
#         "age": 40,
#         "phone": "123",
#         "email": "internal1@example.com",
#         "procedure": "Test Proc",
#         "surgery_date": "2025-01-10",
#         "discharge_date": "2025-01-12",
#         "notes": "ok",
#     })
#     assert r.status_code in (401, 403)  # depends on your auth implementation

# def test_12_register_internal_patient_success_as_admin():
#     r = client.post(
#         "/patients/register-internal",
#         headers=_auth_headers("admin"),
#         json={
#             "mrn": "MRN123456",
#             "name": "Internal Patient",
#             "age": 55,
#             "phone": "+44 7700 900123",
#             "email": "internal.patient@example.com",
#             "procedure": "Colorectal resection",
#             "surgery_date": "2025-01-10",
#             "discharge_date": "2025-01-12",
#             "notes": "Discharged stable",
#         },
#     )
#     assert r.status_code == 200
#     body = r.json()
#     assert body["mrn"] == "MRN123456"
#     assert "temporary_password" in body
#     assert "patient_id" in body

#     # optional DB assertion
#     db = _db()
#     try:
#         row = db.query(PatientMedicalInfo).filter(PatientMedicalInfo.mrn == "MRN123456").first()
#         assert row is not None
#         assert row.patient_id == body["patient_id"]
#     finally:
#         db.close()

# def test_13_register_internal_patient_duplicate_mrn_400():
#     # same MRN as previous test
#     r = client.post(
#         "/patients/register-internal",
#         headers=_auth_headers("admin"),
#         json={
#             "mrn": "MRN123456",
#             "name": "Another Name",
#             "age": 33,
#             "phone": "999",
#             "email": "another.internal@example.com",
#         },
#     )
#     assert r.status_code == 400

# def test_14_register_internal_patient_duplicate_email_400():
#     # same email as previous success test
#     r = client.post(
#         "/patients/register-internal",
#         headers=_auth_headers("admin"),
#         json={
#             "mrn": "MRN999999",
#             "name": "Another Name",
#             "age": 33,
#             "phone": "999",
#             "email": "internal.patient@example.com",
#         },
#     )
#     assert r.status_code == 400


# # ============================================================
# # ROLE API NEGATIVE: create role without admin => 403
# # ============================================================
# def test_15_roles_create_without_admin_returns_403():
#     r = client.post("/roles/", json={"name": "NURSE"}, headers=_auth_headers("patient"))
#     assert r.status_code == 403


# # ============================================================
# # ROLE API CRUD (admin only)
# # ============================================================
# def test_16_roles_crud_as_admin():
#     headers = _auth_headers("admin")

#     # create
#     r = client.post("/roles/", json={"name": "NURSE"}, headers=headers)
#     assert r.status_code == 200
#     role_id = r.json()["role_id"]

#     # list
#     r = client.get("/roles/")
#     assert r.status_code == 200
#     assert any(x["name"] == "NURSE" for x in r.json()["items"])

#     # get
#     r = client.get(f"/roles/{role_id}")
#     assert r.status_code == 200
#     assert r.json()["name"] == "NURSE"

#     # update
#     r = client.put(f"/roles/{role_id}", json={"name": "NURSE_UPDATED"}, headers=headers)
#     assert r.status_code == 200

#     # confirm update
#     r = client.get(f"/roles/{role_id}")
#     assert r.status_code == 200
#     assert r.json()["name"] == "NURSE_UPDATED"

#     # delete
#     r = client.delete(f"/roles/{role_id}", headers=headers)
#     assert r.status_code == 200

#     # confirm delete
#     r = client.get(f"/roles/{role_id}")
#     assert r.status_code == 404


# # ============================================================
# # AUTH NEGATIVE CASES
# # ============================================================
# def test_17_refresh_with_invalid_token_returns_401():
#     r = client.post("/users/refresh", json={"refresh_token": "invalid-refresh-token"})
#     assert r.status_code == 401

# def test_18_change_password_wrong_current_returns_400():
#     r = client.post(
#         "/users/change-password",
#         json={"current_password": "wrong", "new_password": "NewPass123"},
#         headers=_auth_headers("patient"),
#     )
#     assert r.status_code == 400

# def test_19_reset_password_invalid_token_returns_400():
#     r = client.post("/users/reset-password", json={"reset_token": "bad-token", "new_password": "NewPass123"})
#     assert r.status_code == 400


# # ============================================================
# # AUTH POSITIVE CASES
# # ============================================================
# def test_20_refresh_token_success():
#     r = client.post("/users/refresh", json={"refresh_token": STATE["patient"]["refresh"]})
#     assert r.status_code == 200
#     body = r.json()
#     assert "access_token" in body and "refresh_token" in body
#     STATE["patient"]["access"] = body["access_token"]
#     STATE["patient"]["refresh"] = body["refresh_token"]

# def test_21_request_password_reset_success():
#     r = client.post("/users/request-password-reset", json={"email": PATIENT["email"]})
#     assert r.status_code == 200
#     assert "dev_reset_token" in r.json()
#     STATE["patient"]["reset_token"] = r.json()["dev_reset_token"]

# def test_22_reset_password_success():
#     r = client.post("/users/reset-password", json={
#         "reset_token": STATE["patient"]["reset_token"],
#         "new_password": "password123",
#     })
#     assert r.status_code == 200

# def test_23_logout_success():
#     r = client.post("/users/logout", json={"refresh_token": STATE["patient"]["refresh"]})
#     assert r.status_code == 200


# # ============================================================
# # AUDIT LOG TABLE CHECK
# # ============================================================
# def test_24_audit_logs_exist():
#     db = _db()
#     try:
#         assert db.query(AuditLog).count() > 0
#     finally:
#         db.close()

from fastapi.testclient import TestClient

from main import app
from db import Base, engine, SessionLocal

from role import Role
from auth import AuditLog

# NEW: import patient model for DB assertions (optional but useful)
from patients import PatientMedicalInfo

client = TestClient(app)

# ============================================================
# RESET DB (DELETES ALL PREVIOUS TEST DATA)
# ============================================================
def setup_module(module):
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

# ============================================================
# TEST USERS
# ============================================================
PATIENT = {"name": "Patient", "email": "patient2@gmail.com", "password": "password123"}
ADMIN   = {"name": "Admin",   "email": "deasad2019@gmail.com", "password": "12345678"}
DOCTOR  = {"name": "Doctor",  "email": "miangali927@gmail.com", "password": "Ahmed3772"}

STATE = {
    "patient": {"id": None, "verify": None, "access": None, "refresh": None},
    "admin":   {"id": None, "verify": None, "access": None, "refresh": None},
    "doctor":  {"id": None, "verify": None, "access": None, "refresh": None},
}

ROLE_IDS = {"ADMIN": None, "DOCTOR": None, "PATIENT": None}


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
    assert r.status_code == 200
    body = r.json()
    STATE[key]["id"] = body["user_id"]
    STATE[key]["verify"] = body["dev_email_verification_token"]

def _verify(key: str):
    r = client.post("/users/verify-email", json={"token": STATE[key]["verify"]})
    assert r.status_code == 200

def _login(key: str, u: dict, password_override: str | None = None):
    r = client.post("/users/login", json={
        "email": u["email"],
        "password": password_override or u["password"],
    })
    return r

def _login_ok(key: str, u: dict):
    r = _login(key, u)
    assert r.status_code == 200
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


# ============================================================
# POSITIVE FLOW: USERS
# ============================================================
def test_01_register_three_users():
    _register("patient", PATIENT)
    _register("admin", ADMIN)
    _register("doctor", DOCTOR)

def test_02_register_duplicate_email_returns_400():
    r = client.post("/users/register", json={
        "name": "Dup",
        "email": PATIENT["email"],
        "password": "password123",
    })
    assert r.status_code == 400

def test_03_verify_invalid_token_returns_400():
    r = client.post("/users/verify-email", json={"token": "invalid-token"})
    assert r.status_code == 400

def test_04_verify_all_users():
    _verify("patient")
    _verify("admin")
    _verify("doctor")

def test_05_login_wrong_password_returns_401():
    r = _login("patient", PATIENT, password_override="wrong-pass")
    assert r.status_code == 401

def test_06_login_all_users():
    _login_ok("patient", PATIENT)
    _login_ok("admin", ADMIN)
    _login_ok("doctor", DOCTOR)

def test_07_me_works_for_each_user():
    for key, u in [("patient", PATIENT), ("admin", ADMIN), ("doctor", DOCTOR)]:
        r = client.get("/users/me", headers=_auth_headers(key))
        assert r.status_code == 200
        assert r.json()["email"] == u["email"]


# ============================================================
# ROLES BOOTSTRAP (create roles + assign roles)
# ============================================================
def test_08_create_roles_in_db():
    ROLE_IDS["ADMIN"] = _create_role_direct("ADMIN")
    ROLE_IDS["DOCTOR"] = _create_role_direct("DOCTOR")
    ROLE_IDS["PATIENT"] = _create_role_direct("PATIENT")

def test_09_assign_roles_to_users():
    # admin gets ADMIN
    r = client.post("/users/assign-role", json={
        "user_id": STATE["admin"]["id"],
        "role_id": ROLE_IDS["ADMIN"],
    })
    assert r.status_code == 200

    # doctor gets DOCTOR
    r = client.post("/users/assign-role", json={
        "user_id": STATE["doctor"]["id"],
        "role_id": ROLE_IDS["DOCTOR"],
    })
    assert r.status_code == 200

    # patient gets PATIENT
    r = client.post("/users/assign-role", json={
        "user_id": STATE["patient"]["id"],
        "role_id": ROLE_IDS["PATIENT"],
    })
    assert r.status_code == 200

def test_10_remove_role_works():
    # remove PATIENT role from patient
    r = client.post("/users/remove-role", json={
        "user_id": STATE["patient"]["id"],
        "role_id": ROLE_IDS["PATIENT"],
    })
    assert r.status_code == 200

    # confirm removed
    r = client.get("/users/me", headers=_auth_headers("patient"))
    assert r.status_code == 200
    assert "PATIENT" not in r.json()["roles"]

    # add back (so later role counts work)
    r = client.post("/users/assign-role", json={
        "user_id": STATE["patient"]["id"],
        "role_id": ROLE_IDS["PATIENT"],
    })
    assert r.status_code == 200


# ============================================================
# PATIENTS: /patients/register-internal (10 patients)
# ============================================================
def test_11_register_internal_patient_requires_auth_401():
    r = client.post("/patients/register-internal", json={
        "mrn": "MRN0001",
        "name": "Internal One",
        "age": 40,
        "phone": "123",
        "email": "internal1@example.com",
        "procedure": "Test Proc",
        "surgery_date": "2025-01-10",
        "discharge_date": "2025-01-12",
        "notes": "ok",
    })
    assert r.status_code in (401, 403)  # depends on your auth implementation


def test_12_register_10_internal_patients_success_as_admin():
    """
    Creates 10 internal patients with emails:
      test01@gmail.com ... test10@gmail.com
    and MRNs:
      MRNTEST0001 ... MRNTEST0010
    """
    headers = _auth_headers("admin")

    created = []
    for i in range(1, 11):
        email = f"test{i:02d}@gmail.com"
        mrn = f"MRNTEST{i:04d}"
        payload = {
            "mrn": mrn,
            "name": f"Test Patient {i:02d}",
            "age": 30 + i,
            "phone": f"+100000000{i:02d}",
            "email": email,
            "procedure": f"Procedure {i:02d}",
            "surgery_date": "2025-01-10",
            "discharge_date": "2025-01-12",
            "notes": f"Notes for patient {i:02d}",
        }

        r = client.post("/patients/register-internal", headers=headers, json=payload)
        assert r.status_code == 200, r.text
        body = r.json()

        assert body["mrn"] == mrn
        assert "temporary_password" in body
        assert "patient_id" in body

        created.append((mrn, body["patient_id"]))

    # Optional DB assertions: all 10 exist with correct MRNs
    db = _db()
    try:
        for mrn, patient_id in created:
            row = db.query(PatientMedicalInfo).filter(PatientMedicalInfo.mrn == mrn).first()
            assert row is not None
            assert row.patient_id == patient_id
    finally:
        db.close()


def test_13_register_internal_patient_duplicate_mrn_400():
    # duplicate of MRNTEST0001
    r = client.post(
        "/patients/register-internal",
        headers=_auth_headers("admin"),
        json={
            "mrn": "MRNTEST0001",
            "name": "Another Name",
            "age": 33,
            "phone": "999",
            "email": "another.internal@example.com",
        },
    )
    assert r.status_code == 400


def test_14_register_internal_patient_duplicate_email_400():
    # duplicate of test01@gmail.com
    r = client.post(
        "/patients/register-internal",
        headers=_auth_headers("admin"),
        json={
            "mrn": "MRNTEST9999",
            "name": "Another Name",
            "age": 33,
            "phone": "999",
            "email": "test01@gmail.com",
        },
    )
    assert r.status_code == 400


# ============================================================
# ROLE API NEGATIVE: create role without admin => 403
# ============================================================
def test_15_roles_create_without_admin_returns_403():
    r = client.post("/roles/", json={"name": "NURSE"}, headers=_auth_headers("patient"))
    assert r.status_code == 403


# ============================================================
# ROLE API CRUD (admin only)
# ============================================================
def test_16_roles_crud_as_admin():
    headers = _auth_headers("admin")

    # create
    r = client.post("/roles/", json={"name": "NURSE"}, headers=headers)
    assert r.status_code == 200
    role_id = r.json()["role_id"]

    # list
    r = client.get("/roles/")
    assert r.status_code == 200
    assert any(x["name"] == "NURSE" for x in r.json()["items"])

    # get
    r = client.get(f"/roles/{role_id}")
    assert r.status_code == 200
    assert r.json()["name"] == "NURSE"

    # update
    r = client.put(f"/roles/{role_id}", json={"name": "NURSE_UPDATED"}, headers=headers)
    assert r.status_code == 200

    # confirm update
    r = client.get(f"/roles/{role_id}")
    assert r.status_code == 200
    assert r.json()["name"] == "NURSE_UPDATED"

    # delete
    r = client.delete(f"/roles/{role_id}", headers=headers)
    assert r.status_code == 200

    # confirm delete
    r = client.get(f"/roles/{role_id}")
    assert r.status_code == 404


# ============================================================
# AUTH NEGATIVE CASES
# ============================================================
def test_17_refresh_with_invalid_token_returns_401():
    r = client.post("/users/refresh", json={"refresh_token": "invalid-refresh-token"})
    assert r.status_code == 401

def test_18_change_password_wrong_current_returns_400():
    r = client.post(
        "/users/change-password",
        json={"current_password": "wrong", "new_password": "NewPass123"},
        headers=_auth_headers("patient"),
    )
    assert r.status_code == 400

def test_19_reset_password_invalid_token_returns_400():
    r = client.post("/users/reset-password", json={"reset_token": "bad-token", "new_password": "NewPass123"})
    assert r.status_code == 400


# ============================================================
# AUTH POSITIVE CASES
# ============================================================
def test_20_refresh_token_success():
    r = client.post("/users/refresh", json={"refresh_token": STATE["patient"]["refresh"]})
    assert r.status_code == 200
    body = r.json()
    assert "access_token" in body and "refresh_token" in body
    STATE["patient"]["access"] = body["access_token"]
    STATE["patient"]["refresh"] = body["refresh_token"]

def test_21_request_password_reset_success():
    r = client.post("/users/request-password-reset", json={"email": PATIENT["email"]})
    assert r.status_code == 200
    assert "dev_reset_token" in r.json()
    STATE["patient"]["reset_token"] = r.json()["dev_reset_token"]

def test_22_reset_password_success():
    r = client.post("/users/reset-password", json={
        "reset_token": STATE["patient"]["reset_token"],
        "new_password": "password123",
    })
    assert r.status_code == 200

def test_23_logout_success():
    r = client.post("/users/logout", json={"refresh_token": STATE["patient"]["refresh"]})
    assert r.status_code == 200


# ============================================================
# AUDIT LOG TABLE CHECK
# ============================================================
def test_24_audit_logs_exist():
    db = _db()
    try:
        assert db.query(AuditLog).count() > 0
    finally:
        db.close()
