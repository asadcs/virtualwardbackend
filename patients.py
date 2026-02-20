from datetime import datetime, date
from typing import Optional, Dict, List

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from sqlalchemy import Column, Integer, String, Date, Text, DateTime, ForeignKey, or_

from pydantic import BaseModel, EmailStr, Field

from db import Base
from auth import get_db, hash_password, get_current_user, write_audit_log
from user import User

router = APIRouter()

DEFAULT_PATIENT_PASSWORD = "12345678"


class PatientMedicalInfo(Base):
    __tablename__ = "patient_medical_info"

    id = Column(Integer, primary_key=True)
    patient_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)

    mrn = Column(String(50), unique=True, nullable=False, index=True)
    procedure = Column(String(255), nullable=True)

    surgery_date = Column(Date, nullable=True)
    discharge_date = Column(Date, nullable=True)

    notes = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class RegisterInternalPatient(BaseModel):
    mrn: str = Field(min_length=1, max_length=50)
    name: str = Field(min_length=1, max_length=100)
    age: int = Field(ge=0, le=150)                   # not stored yet
    phone: str = Field(min_length=1, max_length=20)  # not stored yet
    email: EmailStr

    procedure: Optional[str] = None
    surgery_date: Optional[date] = None
    discharge_date: Optional[date] = None
    notes: Optional[str] = None


@router.post("/register-internal")
def register_internal_patient(
    data: RegisterInternalPatient,
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    # MRN already exists?
    existing_medical = db.query(PatientMedicalInfo).filter(PatientMedicalInfo.mrn == data.mrn).first()
    if existing_medical:
        raise HTTPException(status_code=400, detail="MRN already exists")

    # Email already exists?
    email = data.email.lower()
    existing_user = db.query(User).filter(User.email == email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    try:
        temp_password = DEFAULT_PATIENT_PASSWORD

        patient_user = User(
            name=data.name,
            email=email,
            password=hash_password(temp_password),
            is_email_verified=True,  # allow login immediately (for now)
        )
        db.add(patient_user)
        db.flush()

        from role import Role
        patient_role = db.query(Role).filter(Role.name == "PATIENT_INTERNAL").first()
        if not patient_role:
            patient_role = Role(name="PATIENT_INTERNAL")
            db.add(patient_role)
            db.flush()

        if patient_role not in patient_user.roles:
            patient_user.roles.append(patient_role)

        db.add(PatientMedicalInfo(
            patient_id=patient_user.id,
            mrn=data.mrn,
            procedure=data.procedure,
            surgery_date=data.surgery_date,
            discharge_date=data.discharge_date,
            notes=data.notes,
        ))

        db.commit()
        db.refresh(patient_user)

        write_audit_log(db, "INTERNAL_PATIENT_REGISTERED", user_id=current_user.id, request=request)

        return {
            "message": "Internal patient registered successfully",
            "patient_id": patient_user.id,
            "temporary_password": temp_password,
            "mrn": data.mrn,
        }

    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to register patient: {str(e)}")


@router.get("/")
def list_patients(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
    q: str | None = None,
    skip: int = 0,
    limit: int = 20,
    sort: str = "name",
    order: str = "asc",
    include_assignments: int = 0,  # ✅ NEW
):
    """
    Returns patient rows for admin UI.

    If include_assignments=1, each item includes:
      assignments: [
        { id, questionnaire_template_id, questionnaire_template_name, start_date, end_date, status }
      ]

    sort supports: name, mrn, created_at, assigned_count
    """

    # base query
    query = db.query(PatientMedicalInfo, User).join(User, User.id == PatientMedicalInfo.patient_id)

    if q:
        like = f"%{q}%"
        query = query.filter(or_(
            User.name.ilike(like),
            User.email.ilike(like),
            PatientMedicalInfo.mrn.ilike(like),
            PatientMedicalInfo.procedure.ilike(like),
        ))

    # normal sorts (assigned_count handled later)
    sort_map = {
        "name": User.name,
        "mrn": PatientMedicalInfo.mrn,
        "created_at": PatientMedicalInfo.created_at,
    }
    sort_col = sort_map.get(sort, User.name)

    # pagination first compute total
    total = query.count()
    rows = query.offset(skip).limit(min(limit, 100)).all()

    # build patient items (without assignments first)
    items: list[dict] = []
    patient_ids: list[int] = []

    for med, user in rows:
        patient_ids.append(user.id)
        items.append({
            "patient_id": user.id,
            "name": user.name,
            "email": user.email,
            "mrn": med.mrn,
            "procedure": med.procedure,
            "surgery_date": med.surgery_date.isoformat() if med.surgery_date else None,
            "discharge_date": med.discharge_date.isoformat() if med.discharge_date else None,
            "created_at": med.created_at.isoformat() if med.created_at else None,
            "status": "Verified" if user.is_email_verified else "Pending",
            "assignments": [],  # ✅ always present for UI simplicity
        })

    # include assignments if requested
    assignment_map: Dict[int, list] = {}
    active_count_map: Dict[int, int] = {}

    if include_assignments and patient_ids:
        from assignments import QuestionnaireAssignment
        from flows import QuestionnaireFlow

        # ✅ template_id now points to questionnaire_flows.id (compatibility)
        a_rows = (
            db.query(QuestionnaireAssignment, QuestionnaireFlow)
            .join(QuestionnaireFlow, QuestionnaireFlow.id == QuestionnaireAssignment.template_id)
            .filter(QuestionnaireAssignment.patient_id.in_(patient_ids))
            .order_by(QuestionnaireAssignment.created_at.desc())
            .all()
        )

        for a, f in a_rows:
            assignment_map.setdefault(a.patient_id, []).append({
                "id": a.id,
                "questionnaire_template_id": a.template_id,     # ⚠️ actually flow_id (kept for compatibility)
                "questionnaire_template_name": f.name,          # ✅ flow name
                "start_date": a.start_date.isoformat() if a.start_date else None,
                "end_date": a.end_date.isoformat() if a.end_date else None,
                "status": "ACTIVE" if bool(a.is_active) else "INACTIVE",
            })
            if bool(a.is_active):
                active_count_map[a.patient_id] = active_count_map.get(a.patient_id, 0) + 1

        for it in items:
            pid = it["patient_id"]
            it["assignments"] = assignment_map.get(pid, [])

        # ✅ if sorting by assigned_count, sort in python using active_count_map
        if sort == "assigned_count":
            reverse = (order.lower() == "desc")
            items.sort(key=lambda x: active_count_map.get(x["patient_id"], 0), reverse=reverse)
        else:
            # otherwise apply DB sort order manually to current page items (already in DB order)
            pass

    # apply DB sort for non-assigned_count
    if sort != "assigned_count":
        # NOTE: DB sort must be applied before pagination, so we re-run query properly here:
        query2 = db.query(PatientMedicalInfo, User).join(User, User.id == PatientMedicalInfo.patient_id)
        if q:
            like = f"%{q}%"
            query2 = query2.filter(or_(
                User.name.ilike(like),
                User.email.ilike(like),
                PatientMedicalInfo.mrn.ilike(like),
                PatientMedicalInfo.procedure.ilike(like),
            ))

        query2 = query2.order_by(sort_col.desc() if order.lower() == "desc" else sort_col.asc())
        rows2 = query2.offset(skip).limit(min(limit, 100)).all()

        # rebuild items in correct order but keep assignments if we already computed them
        rebuilt: list[dict] = []
        for med, user in rows2:
            row = next((x for x in items if x["patient_id"] == user.id), None)
            if not row:
                row = {
                    "patient_id": user.id,
                    "name": user.name,
                    "email": user.email,
                    "mrn": med.mrn,
                    "procedure": med.procedure,
                    "surgery_date": med.surgery_date.isoformat() if med.surgery_date else None,
                    "discharge_date": med.discharge_date.isoformat() if med.discharge_date else None,
                    "created_at": med.created_at.isoformat() if med.created_at else None,
                    "status": "Verified" if user.is_email_verified else "Pending",
                    "assignments": assignment_map.get(user.id, []) if include_assignments else [],
                }
            rebuilt.append(row)
        items = rebuilt

    return {"total": total, "items": items}
