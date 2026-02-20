from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import or_

from auth import (
    get_db,
    get_current_user,
    hash_password,
    write_audit_log,
    RefreshToken,
    AuditLog,
)
from user import User, PasswordResetToken
from patients import PatientMedicalInfo

router = APIRouter(prefix="/demo-admin", tags=["Demo Admin"])

DEFAULT_PASSWORD = "12345678"


# ============================================================
# HELPERS
# ============================================================
def _is_admin(user: User) -> bool:
    role_names = {r.name for r in getattr(user, "roles", []) or []}
    return ("ADMIN" in role_names) or ("SUPER_ADMIN" in role_names)


def _require_admin(current_user: User):
    if not _is_admin(current_user):
        raise HTTPException(status_code=403, detail="Admin access required")


# ============================================================
# SCHEMAS
# ============================================================
class DemoWipeAndSeedRequest(BaseModel):
    count: int = Field(default=10, ge=1, le=50)
    password: str = Field(default=DEFAULT_PASSWORD, min_length=8, max_length=64)

    # TEST_EMAILS => only test01..test50@gmail.com (safe)
    # ALL_INTERNAL => delete ALL users with role PATIENT_INTERNAL (dangerous)
    wipe_scope: str = Field(default="TEST_EMAILS")  # TEST_EMAILS | ALL_INTERNAL
    email_domain: str = Field(default="gmail.com")


class DemoWipeAndSeedResponse(BaseModel):
    deleted_users: int
    deleted_refresh_tokens: int
    deleted_password_reset_tokens: int
    deleted_audit_logs: int
    deleted_medical: int
    deleted_assignments: int
    deleted_instances: int
    deleted_answers: int
    deleted_notifications: int

    created_users: int
    emails: list[str]
    password: str


class DemoDeleteAllPatientsRequest(BaseModel):
    # TEST_EMAILS => only test01..test50@gmail.com (safe)
    # ALL_INTERNAL => delete ALL PATIENT_INTERNAL users (dangerous)
    scope: str = Field(default="TEST_EMAILS")  # TEST_EMAILS | ALL_INTERNAL
    email_domain: str = Field(default="gmail.com")


class DemoDeleteAllPatientsResponse(BaseModel):
    deleted_users: int
    deleted_refresh_tokens: int
    deleted_password_reset_tokens: int
    deleted_audit_logs: int
    deleted_medical: int
    deleted_assignments: int
    deleted_instances: int
    deleted_answers: int
    deleted_notifications: int


# ============================================================
# INTERNAL DELETE CORE (shared)
# ============================================================
def _delete_patients_by_scope(
    db: Session,
    *,
    scope: str,
    email_domain: str,
) -> tuple[int, int, int, int, int, int, int, int, int]:
    """
    Returns:
      deleted_users,
      deleted_refresh,
      deleted_reset,
      deleted_audit_logs,
      deleted_medical,
      deleted_assignments,
      deleted_instances,
      deleted_answers,
      deleted_notifications
    """
    # local imports to avoid circular imports
    from role import Role
    from assignments import QuestionnaireAssignment
    from patient_dashboard import QuestionnaireInstance, QuestionnaireAnswer
    from admin_monitoring import AdminNotification  # FK: instance_id -> questionnaire_instances.id

    # ensure role exists
    patient_role = db.query(Role).filter(Role.name == "PATIENT_INTERNAL").first()
    if not patient_role:
        patient_role = Role(name="PATIENT_INTERNAL")
        db.add(patient_role)
        db.flush()

    demo_emails = [f"test{i:02d}@{email_domain}" for i in range(1, 51)]

    # 1) select users
    if scope == "ALL_INTERNAL":
        all_users = db.query(User).all()
        users_to_delete = [u for u in all_users if patient_role in (u.roles or [])]
    else:
        users_to_delete = db.query(User).filter(User.email.in_(demo_emails)).all()

    user_ids = [u.id for u in users_to_delete]

    deleted_answers = 0
    deleted_instances = 0
    deleted_assignments = 0
    deleted_refresh = 0
    deleted_reset = 0
    deleted_audit_logs = 0
    deleted_medical = 0
    deleted_notifications = 0

    if user_ids:
        # ✅ IMPORTANT:
        # admin_notifications.instance_id has FK -> questionnaire_instances.id
        # So we MUST delete notifications first.

        instance_ids = [
            r[0]
            for r in db.query(QuestionnaireInstance.id)
            .filter(QuestionnaireInstance.patient_id.in_(user_ids))
            .all()
        ]

        notif_filter = [AdminNotification.patient_id.in_(user_ids)]
        if instance_ids:
            notif_filter.append(AdminNotification.instance_id.in_(instance_ids))

        deleted_notifications = (
            db.query(AdminNotification)
            .filter(or_(*notif_filter))
            .delete(synchronize_session=False)
        )

        # Delete in correct FK order:
        # notifications -> answers -> instances -> assignments -> auth -> audit -> medical -> users

        deleted_answers = (
            db.query(QuestionnaireAnswer)
            .filter(QuestionnaireAnswer.patient_id.in_(user_ids))
            .delete(synchronize_session=False)
        )

        deleted_instances = (
            db.query(QuestionnaireInstance)
            .filter(QuestionnaireInstance.patient_id.in_(user_ids))
            .delete(synchronize_session=False)
        )

        deleted_assignments = (
            db.query(QuestionnaireAssignment)
            .filter(QuestionnaireAssignment.patient_id.in_(user_ids))
            .delete(synchronize_session=False)
        )

        deleted_refresh = (
            db.query(RefreshToken)
            .filter(RefreshToken.user_id.in_(user_ids))
            .delete(synchronize_session=False)
        )

        deleted_reset = (
            db.query(PasswordResetToken)
            .filter(PasswordResetToken.user_id.in_(user_ids))
            .delete(synchronize_session=False)
        )

        deleted_audit_logs = (
            db.query(AuditLog)
            .filter(AuditLog.user_id.in_(user_ids))
            .delete(synchronize_session=False)
        )

        deleted_medical = (
            db.query(PatientMedicalInfo)
            .filter(PatientMedicalInfo.patient_id.in_(user_ids))
            .delete(synchronize_session=False)
        )

    # delete users (clear roles)
    for u in users_to_delete:
        try:
            if getattr(u, "roles", None) is not None:
                u.roles.clear()
        except Exception:
            pass
        db.delete(u)

    deleted_users = len(users_to_delete)
    db.flush()

    return (
        deleted_users,
        deleted_refresh,
        deleted_reset,
        deleted_audit_logs,
        deleted_medical,
        deleted_assignments,
        deleted_instances,
        deleted_answers,
        deleted_notifications,
    )


# ============================================================
# ROUTES
# ============================================================
@router.post("/wipe-and-seed", response_model=DemoWipeAndSeedResponse)
def wipe_and_seed_demo_patients(
    payload: DemoWipeAndSeedRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_admin(current_user)
    from role import Role  # local import

    try:
        (
            deleted_users,
            deleted_refresh,
            deleted_reset,
            deleted_audit_logs,
            deleted_medical,
            deleted_assignments,
            deleted_instances,
            deleted_answers,
            deleted_notifications,
        ) = _delete_patients_by_scope(
            db,
            scope=payload.wipe_scope,
            email_domain=payload.email_domain,
        )

        # ensure role exists for new users
        patient_role = db.query(Role).filter(Role.name == "PATIENT_INTERNAL").first()
        if not patient_role:
            patient_role = Role(name="PATIENT_INTERNAL")
            db.add(patient_role)
            db.flush()

        created_emails: list[str] = []

        for i in range(1, payload.count + 1):
            email = f"test{i:02d}@{payload.email_domain}"
            mrn = f"MRNTEST{i:04d}"

            if db.query(User).filter(User.email == email).first():
                raise HTTPException(status_code=400, detail=f"Email already exists: {email}")
            if db.query(PatientMedicalInfo).filter(PatientMedicalInfo.mrn == mrn).first():
                raise HTTPException(status_code=400, detail=f"MRN already exists: {mrn}")

            u = User(
                name=f"Test Patient {i:02d}",
                email=email,
                password=hash_password(payload.password),
                is_email_verified=True,
            )
            db.add(u)
            db.flush()

            if patient_role not in (u.roles or []):
                u.roles.append(patient_role)

            db.add(
                PatientMedicalInfo(
                    patient_id=u.id,
                    mrn=mrn,
                    procedure=f"Demo Procedure {i:02d}",
                    surgery_date=date(2025, 1, 10),
                    discharge_date=date(2025, 1, 12),
                    notes="Seeded demo patient",
                )
            )

            created_emails.append(email)

        db.commit()
        write_audit_log(db, "DEMO_WIPE_AND_SEED", user_id=current_user.id, request=request)

        return DemoWipeAndSeedResponse(
            deleted_users=deleted_users,
            deleted_refresh_tokens=deleted_refresh,
            deleted_password_reset_tokens=deleted_reset,
            deleted_audit_logs=deleted_audit_logs,
            deleted_medical=deleted_medical,
            deleted_assignments=deleted_assignments,
            deleted_instances=deleted_instances,
            deleted_answers=deleted_answers,
            deleted_notifications=deleted_notifications,
            created_users=len(created_emails),
            emails=created_emails,
            password=payload.password,
        )

    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Demo wipe/seed failed: {str(e)}")


@router.post("/delete-all-patients", response_model=DemoDeleteAllPatientsResponse)
def delete_all_patients(
    payload: DemoDeleteAllPatientsRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_admin(current_user)

    try:
        (
            deleted_users,
            deleted_refresh,
            deleted_reset,
            deleted_audit_logs,
            deleted_medical,
            deleted_assignments,
            deleted_instances,
            deleted_answers,
            deleted_notifications,
        ) = _delete_patients_by_scope(
            db,
            scope=payload.scope,
            email_domain=payload.email_domain,
        )

        db.commit()
        write_audit_log(db, "DEMO_DELETE_ALL_PATIENTS", user_id=current_user.id, request=request)

        return DemoDeleteAllPatientsResponse(
            deleted_users=deleted_users,
            deleted_refresh_tokens=deleted_refresh,
            deleted_password_reset_tokens=deleted_reset,
            deleted_audit_logs=deleted_audit_logs,
            deleted_medical=deleted_medical,
            deleted_assignments=deleted_assignments,
            deleted_instances=deleted_instances,
            deleted_answers=deleted_answers,
            deleted_notifications=deleted_notifications,
        )

    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Delete all patients failed: {str(e)}")
