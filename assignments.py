# assignments.py
from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import (
    Column,
    Integer,
    Date,
    DateTime,
    Boolean,
    ForeignKey,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Session

from db import Base
from auth import get_db, get_current_user, require_admin, write_audit_log
from user import User
from patients import PatientMedicalInfo

# ✅ Flow models (confirm your real filename: flows.py vs flow.py)
from flows import QuestionnaireFlow, FlowStatus  # change to: from flow import ... if needed


router = APIRouter(prefix="/assignments", tags=["Assignments"])


# ============================================================
# MODEL
# ============================================================
class AssignmentFrequency(str, Enum):
    DAILY = "DAILY"
    WEEKLY = "WEEKLY"  # optional later


class QuestionnaireAssignment(Base):
    """
    A monitoring plan record:
      Patient X is assigned Flow Y from start_date to end_date.
    """
    __tablename__ = "questionnaire_assignments"
    __table_args__ = (
        UniqueConstraint("patient_id", "flow_id", "start_date", "end_date", name="uq_assignment_range"),
    )

    id = Column(Integer, primary_key=True)

    patient_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    # ✅ Flow FK (no more template naming)
    flow_id = Column(Integer, ForeignKey("questionnaire_flows.id"), nullable=False, index=True)

    start_date = Column(Date, nullable=False, index=True)
    end_date = Column(Date, nullable=False, index=True)

    frequency = Column(String(20), nullable=False, default=AssignmentFrequency.DAILY.value)
    is_active = Column(Boolean, default=True, nullable=False)

    created_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


# ============================================================
# SCHEMAS
# ============================================================
class AssignmentCreateIn(BaseModel):
    patient_id: int
    flow_id: int
    start_date: date
    end_date: date
    frequency: AssignmentFrequency = AssignmentFrequency.DAILY


class AssignmentOut(BaseModel):
    id: int
    patient_id: int
    flow_id: int
    flow_name: str
    flow_type: str
    start_date: date
    end_date: date
    frequency: str
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class AssignmentListOut(BaseModel):
    total: int
    items: List[AssignmentOut]


# ============================================================
# HELPERS
# ============================================================
def _ensure_patient_exists(db: Session, patient_id: int):
    u = db.query(User).filter(User.id == patient_id).first()
    if not u:
        raise HTTPException(status_code=404, detail="Patient user not found")

    med = db.query(PatientMedicalInfo).filter(PatientMedicalInfo.patient_id == patient_id).first()
    if not med:
        raise HTTPException(status_code=404, detail="Patient medical record not found")

    return u, med


def _ensure_flow_exists(db: Session, flow_id: int) -> QuestionnaireFlow:
    f = (
        db.query(QuestionnaireFlow)
        .filter(
            QuestionnaireFlow.id == flow_id,
            QuestionnaireFlow.is_deleted == False,  # noqa: E712
        )
        .first()
    )
    if not f:
        raise HTTPException(status_code=404, detail="Questionnaire flow not found")

    if getattr(f, "status", None) != FlowStatus.ACTIVE:
        raise HTTPException(status_code=400, detail="Only ACTIVE flows can be assigned")

    return f


# ============================================================
# ROUTES
# ============================================================
@router.post("/", response_model=dict)
def assign_flow_to_patient(
    payload: AssignmentCreateIn,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_admin(current_user)

    if payload.end_date < payload.start_date:
        raise HTTPException(status_code=400, detail="end_date must be >= start_date")

    patient_user, _med = _ensure_patient_exists(db, payload.patient_id)
    flow = _ensure_flow_exists(db, payload.flow_id)

    row = QuestionnaireAssignment(
        patient_id=payload.patient_id,
        flow_id=payload.flow_id,
        start_date=payload.start_date,
        end_date=payload.end_date,
        frequency=payload.frequency.value,
        is_active=True,
        created_by_user_id=current_user.id,
    )

    db.add(row)
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(status_code=400, detail="Assignment already exists or invalid")

    db.refresh(row)

    write_audit_log(
        db,
        "FLOW_ASSIGNED",
        user_id=current_user.id,
        request=request,
        details=f"patient_id={patient_user.id}, flow_id={flow.id}",
    )

    return {"assignment_id": row.id}


@router.get("/patient/{patient_id}", response_model=AssignmentListOut)
def list_assignments_for_patient_admin(
    patient_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    active_only: bool = True,
    skip: int = 0,
    limit: int = 50,
):
    require_admin(current_user)
    _ensure_patient_exists(db, patient_id)

    q = (
        db.query(QuestionnaireAssignment, QuestionnaireFlow)
        .join(QuestionnaireFlow, QuestionnaireFlow.id == QuestionnaireAssignment.flow_id)
        .filter(QuestionnaireAssignment.patient_id == patient_id)
    )

    if active_only:
        q = q.filter(QuestionnaireAssignment.is_active == True)  # noqa: E712

    total = q.count()
    rows = (
        q.order_by(QuestionnaireAssignment.created_at.desc())
        .offset(skip)
        .limit(min(limit, 100))
        .all()
    )

    items: List[AssignmentOut] = []
    for a, f in rows:
        items.append(
            AssignmentOut(
                id=a.id,
                patient_id=a.patient_id,
                flow_id=a.flow_id,
                flow_name=f.name,
                flow_type=str(f.flow_type),
                start_date=a.start_date,
                end_date=a.end_date,
                frequency=a.frequency,
                is_active=a.is_active,
                created_at=a.created_at,
            )
        )

    return AssignmentListOut(total=total, items=items)


@router.get("/me", response_model=AssignmentListOut)
def list_my_assignments(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    active_only: bool = True,
    today_only: bool = False,
    skip: int = 0,
    limit: int = 50,
):
    q = (
        db.query(QuestionnaireAssignment, QuestionnaireFlow)
        .join(QuestionnaireFlow, QuestionnaireFlow.id == QuestionnaireAssignment.flow_id)
        .filter(QuestionnaireAssignment.patient_id == current_user.id)
    )

    if active_only:
        q = q.filter(QuestionnaireAssignment.is_active == True)  # noqa: E712

    if today_only:
        today = date.today()
        q = q.filter(
            QuestionnaireAssignment.start_date <= today,
            QuestionnaireAssignment.end_date >= today,
        )

    total = q.count()
    rows = (
        q.order_by(QuestionnaireAssignment.created_at.desc())
        .offset(skip)
        .limit(min(limit, 100))
        .all()
    )

    items: List[AssignmentOut] = []
    for a, f in rows:
        items.append(
            AssignmentOut(
                id=a.id,
                patient_id=a.patient_id,
                flow_id=a.flow_id,
                flow_name=f.name,
                flow_type=str(f.flow_type),
                start_date=a.start_date,
                end_date=a.end_date,
                frequency=a.frequency,
                is_active=a.is_active,
                created_at=a.created_at,
            )
        )

    return AssignmentListOut(total=total, items=items)


@router.post("/{assignment_id}/deactivate", response_model=dict)
def deactivate_assignment(
    assignment_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_admin(current_user)

    a = db.query(QuestionnaireAssignment).filter(QuestionnaireAssignment.id == assignment_id).first()
    if not a:
        raise HTTPException(status_code=404, detail="Assignment not found")

    a.is_active = False
    db.commit()

    write_audit_log(
        db,
        "FLOW_UNASSIGNED",
        user_id=current_user.id,
        request=request,
        details=f"assignment_id={assignment_id}",
    )

    return {"message": "Assignment deactivated"}
