from __future__ import annotations

import os
from datetime import date, datetime, time, timedelta
from typing import Dict, List, Optional, Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, UniqueConstraint, Index
from sqlalchemy.orm import Session, relationship

from db import Base
from auth import get_db, get_current_user, require_admin
from user import User
from assignments import QuestionnaireAssignment
from patient_dashboard import QuestionnaireInstance, QuestionnaireAnswer, CheckinStatus

# ✅ NEW: flow option scoring instead of QuestionnaireOption
from flows import FlowNodeOption

try:
    from zoneinfo import ZoneInfo
    from zoneinfo import ZoneInfoNotFoundError
except Exception:
    ZoneInfo = None  # type: ignore
    ZoneInfoNotFoundError = Exception  # type: ignore


router = APIRouter(prefix="/admin", tags=["Admin Monitoring"])


# ============================================================
# Persistent admin notifications (DB model)
# ============================================================
class AdminNotification(Base):
    __tablename__ = "admin_notifications"
    __table_args__ = (
        UniqueConstraint("type", "instance_id", name="uq_adminnotif_type_instance"),
        Index("ix_adminnotif_seen_at", "seen_at"),
        Index("ix_adminnotif_created_at", "created_at"),
        Index("ix_adminnotif_patient_id", "patient_id"),
    )

    id = Column(Integer, primary_key=True)

    type = Column(String(50), nullable=False, index=True)  # NEW_SUBMISSION, AMBER_ALERT, RED_ALERT
    severity = Column(String(20), nullable=False, default="INFO", index=True)  # INFO, AMBER, RED

    patient_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    instance_id = Column(Integer, ForeignKey("questionnaire_instances.id"), nullable=True, index=True)

    message = Column(String(500), nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    seen_at = Column(DateTime, nullable=True)
    seen_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    patient = relationship("User", foreign_keys=[patient_id])
    seen_by = relationship("User", foreign_keys=[seen_by_user_id])
    instance = relationship("QuestionnaireInstance", foreign_keys=[instance_id])


# ============================================================
# Schemas
# ============================================================
class DashboardStatsOut(BaseModel):
    activePatients: int
    internalPatients: int
    externalPatients: int
    pendingRegistrations: int

    todaySubmissions: int
    totalExpected: int

    # score-based
    redAlerts: int
    amberAlerts: int

    unseenNotifications: int
    newSubmissionsToday: int


TodayStatus = Literal["DUE", "COMPLETED", "MISSED", "NO_CHECKIN"]


class MonitoringRowOut(BaseModel):
    patient_id: int
    patient_name: str
    patient_email: str
    today_status: TodayStatus
    submitted_at: Optional[str] = None

    total_score: int
    severity: Literal["GREEN", "AMBER", "RED"]


class AlertsOut(BaseModel):
    patient_id: int
    patient_name: str
    severity: Literal["AMBER", "RED"]
    reason: str


class AdminNotificationOut(BaseModel):
    id: int
    type: str
    severity: str
    patient_id: int
    patient_name: str
    instance_id: Optional[int] = None
    message: str
    created_at: str
    seen_at: Optional[str] = None


class NotificationCountOut(BaseModel):
    unseen: int


# -------------------------
# Time helpers
# -------------------------
def _get_tz():
    tz_key = os.getenv("HOSPITAL_TIMEZONE", "Europe/Lisbon")
    if ZoneInfo is None:
        return None
    try:
        return ZoneInfo(tz_key)
    except ZoneInfoNotFoundError:
        return ZoneInfo("UTC")


def _local_now() -> datetime:
    fake = os.getenv("DEV_NOW")
    tz = _get_tz()

    if fake:
        dt = datetime.fromisoformat(fake)
        return dt.replace(tzinfo=tz) if tz else dt

    return datetime.now(tz=tz) if tz else datetime.utcnow()


def _cutoff() -> time:
    raw = os.getenv("DAILY_CHECKIN_CUTOFF_LOCAL_TIME", "11:00")
    hh, mm = raw.split(":")
    return time(hour=int(hh), minute=int(mm))


def _before_cutoff(now: datetime) -> bool:
    return now.time() < _cutoff()


# -------------------------
# Core queries
# -------------------------
def _patients_expected_today(db: Session, today: date) -> List[int]:
    rows = (
        db.query(QuestionnaireAssignment.patient_id)
        .filter(
            QuestionnaireAssignment.is_active == True,  # noqa: E712
            QuestionnaireAssignment.start_date <= today,
            QuestionnaireAssignment.end_date >= today,
        )
        .distinct()
        .all()
    )
    return [r[0] for r in rows]


def _instances_completed_today_patient_ids(db: Session, today: date) -> List[int]:
    rows = (
        db.query(QuestionnaireInstance.patient_id)
        .filter(
            QuestionnaireInstance.scheduled_for == today,
            QuestionnaireInstance.status == CheckinStatus.COMPLETED,
        )
        .distinct()
        .all()
    )
    return [r[0] for r in rows]


def _instances_completed_today_by_patient(db: Session, today: date) -> Dict[int, QuestionnaireInstance]:
    rows = (
        db.query(QuestionnaireInstance)
        .filter(
            QuestionnaireInstance.scheduled_for == today,
            QuestionnaireInstance.status == CheckinStatus.COMPLETED,
        )
        .all()
    )
    out: Dict[int, QuestionnaireInstance] = {}
    for inst in rows:
        prev = out.get(inst.patient_id)
        if not prev:
            out[inst.patient_id] = inst
        else:
            prev_ts = prev.submitted_at or prev.created_at
            cur_ts = inst.submitted_at or inst.created_at
            if cur_ts and prev_ts and cur_ts > prev_ts:
                out[inst.patient_id] = inst
    return out


def _today_status_for_patient(
    patient_id: int,
    today: date,
    now: datetime,
    todays_assignments: List[QuestionnaireAssignment],
    completed_map: Dict[int, QuestionnaireInstance],
) -> tuple[TodayStatus, Optional[QuestionnaireInstance]]:
    if not todays_assignments:
        return "NO_CHECKIN", None

    inst = completed_map.get(patient_id)
    if inst:
        return "COMPLETED", inst

    if _before_cutoff(now):
        return "DUE", None
    return "MISSED", None


# -------------------------
# Score helpers (today score)
# -------------------------
def _today_total_score_for_patient(db: Session, *, patient_id: int, today: date) -> int:
    inst_ids = [
        r[0]
        for r in db.query(QuestionnaireInstance.id)
        .filter(
            QuestionnaireInstance.patient_id == patient_id,
            QuestionnaireInstance.scheduled_for == today,
            QuestionnaireInstance.status == CheckinStatus.COMPLETED,
        )
        .all()
    ]
    if not inst_ids:
        return 0

    option_ids = [
        r[0]
        for r in db.query(QuestionnaireAnswer.option_id)
        .filter(
            QuestionnaireAnswer.instance_id.in_(inst_ids),
            QuestionnaireAnswer.patient_id == patient_id,
            QuestionnaireAnswer.option_id.isnot(None),
        )
        .all()
        if r and r[0] is not None
    ]
    if not option_ids:
        return 0

    # ✅ flows scoring: seriousness_points is the closest replacement for old "score"
    pts = db.query(FlowNodeOption.seriousness_points).filter(FlowNodeOption.id.in_(option_ids)).all()
    return sum(int(p[0] or 0) for p in pts)


def _score_severity(total_score: int) -> str:
    # ✅ Your rules:
    # GREEN: <5, AMBER: ==5, RED: >5
    if total_score > 5:
        return "RED"
    if total_score == 5:
        return "AMBER"
    return "GREEN"


def _count_registered_patients(db: Session) -> tuple[int, int, int]:
    users = db.query(User).all()
    total = 0
    internal = 0
    external = 0
    for u in users:
        role_names = {r.name for r in getattr(u, "roles", [])}
        if "PATIENT_INTERNAL" in role_names:
            total += 1
            internal += 1
        elif "PATIENT" in role_names:
            total += 1
            external += 1
    return total, internal, external


# ============================================================
# Notifications helpers
# ============================================================
def _unseen_notifications_count(db: Session) -> int:
    return db.query(AdminNotification).filter(AdminNotification.seen_at.is_(None)).count()


def _new_submissions_today_count_utc(db: Session) -> int:
    now_utc = datetime.utcnow()
    start = datetime.combine(now_utc.date(), time(0, 0, 0))
    end = start + timedelta(days=1)

    return (
        db.query(AdminNotification)
        .filter(
            AdminNotification.type == "NEW_SUBMISSION",
            AdminNotification.created_at >= start,
            AdminNotification.created_at < end,
        )
        .count()
    )


# ============================================================
# Routes
# ============================================================
@router.get("/dashboard-stats", response_model=DashboardStatsOut)
def admin_dashboard_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_admin(current_user)

    now = _local_now()
    today = now.date()

    # expected today
    expected_patient_ids = _patients_expected_today(db, today)
    total_expected = len(expected_patient_ids)

    # submissions today
    completed_patient_ids = _instances_completed_today_patient_ids(db, today)
    today_submissions = len(completed_patient_ids)

    # ✅ registered patients (not expected-today)
    active_patients, internal, external = _count_registered_patients(db)

    # pending registrations (kept from your logic)
    pending = 0
    maybe_pending = db.query(User).filter(User.is_email_verified == False).all()  # noqa: E712
    for u in maybe_pending:
        role_names = {r.name for r in getattr(u, "roles", [])}
        if "PATIENT" in role_names:
            pending += 1

    # ✅ score-based alert counts (only among today's submissions)
    red = 0
    amber = 0
    for pid in completed_patient_ids:
        score = _today_total_score_for_patient(db, patient_id=pid, today=today)
        sev = _score_severity(score)
        if sev == "RED":
            red += 1
        elif sev == "AMBER":
            amber += 1

    unseen = _unseen_notifications_count(db)
    new_sub_today = _new_submissions_today_count_utc(db)

    return DashboardStatsOut(
        activePatients=active_patients,
        internalPatients=internal,
        externalPatients=external,
        pendingRegistrations=pending,
        todaySubmissions=today_submissions,
        totalExpected=total_expected,
        redAlerts=red,
        amberAlerts=amber,
        unseenNotifications=unseen,
        newSubmissionsToday=new_sub_today,
    )


@router.get("/monitoring/today", response_model=List[MonitoringRowOut])
def admin_monitoring_today(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_admin(current_user)

    now = _local_now()
    today = now.date()

    expected_patient_ids = _patients_expected_today(db, today)
    if not expected_patient_ids:
        return []

    users = db.query(User).filter(User.id.in_(expected_patient_ids)).all()
    user_map = {u.id: u for u in users}

    completed_map = _instances_completed_today_by_patient(db, today)

    rows: List[MonitoringRowOut] = []
    for pid in expected_patient_ids:
        u = user_map.get(pid)
        if not u:
            continue

        todays_assignments = (
            db.query(QuestionnaireAssignment)
            .filter(
                QuestionnaireAssignment.patient_id == pid,
                QuestionnaireAssignment.is_active == True,  # noqa: E712
                QuestionnaireAssignment.start_date <= today,
                QuestionnaireAssignment.end_date >= today,
            )
            .all()
        )

        today_status, inst = _today_status_for_patient(pid, today, now, todays_assignments, completed_map)

        submitted_at = None
        total_score = 0
        severity = "GREEN"

        if today_status == "COMPLETED":
            if inst and inst.submitted_at:
                submitted_at = inst.submitted_at.isoformat()
            total_score = _today_total_score_for_patient(db, patient_id=pid, today=today)
            severity = _score_severity(total_score)

        rows.append(
            MonitoringRowOut(
                patient_id=pid,
                patient_name=u.name,
                patient_email=u.email,
                today_status=today_status,
                submitted_at=submitted_at,
                total_score=total_score,
                severity=severity,
            )
        )

    priority = {"RED": 0, "AMBER": 1, "GREEN": 2}
    rows.sort(key=lambda r: (priority[r.severity], r.patient_name.lower()))
    return rows


@router.get("/alerts", response_model=List[AlertsOut])
def admin_alerts(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_admin(current_user)

    now = _local_now()
    today = now.date()

    completed_patient_ids = _instances_completed_today_patient_ids(db, today)
    if not completed_patient_ids:
        return []

    users = db.query(User).filter(User.id.in_(completed_patient_ids)).all()
    user_map = {u.id: u for u in users}

    alerts: List[AlertsOut] = []
    for pid in completed_patient_ids:
        u = user_map.get(pid)
        if not u:
            continue

        score = _today_total_score_for_patient(db, patient_id=pid, today=today)
        sev = _score_severity(score)
        if sev == "GREEN":
            continue

        alerts.append(
            AlertsOut(
                patient_id=pid,
                patient_name=u.name,
                severity="RED" if sev == "RED" else "AMBER",
                reason=f"Today score = {score}",
            )
        )

    alerts.sort(key=lambda a: (0 if a.severity == "RED" else 1, a.patient_name.lower()))
    return alerts


@router.get("/notifications/count", response_model=NotificationCountOut)
def notifications_count(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_admin(current_user)
    return NotificationCountOut(unseen=_unseen_notifications_count(db))


@router.get("/notifications", response_model=List[AdminNotificationOut])
def list_notifications(
    unseen_only: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_admin(current_user)

    q = db.query(AdminNotification).join(User, User.id == AdminNotification.patient_id)

    if unseen_only:
        q = q.filter(AdminNotification.seen_at.is_(None))

    rows = (
        q.order_by(AdminNotification.created_at.desc())
        .limit(min(max(limit, 1), 200))
        .all()
    )

    out: List[AdminNotificationOut] = []
    for r in rows:
        out.append(
            AdminNotificationOut(
                id=r.id,
                type=r.type,
                severity=r.severity,
                patient_id=r.patient_id,
                patient_name=r.patient.name if r.patient else "—",
                instance_id=r.instance_id,
                message=r.message,
                created_at=r.created_at.isoformat(),
                seen_at=r.seen_at.isoformat() if r.seen_at else None,
            )
        )

    return out


@router.post("/notifications/{notification_id}/mark-seen", response_model=dict)
def mark_notification_seen(
    notification_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_admin(current_user)

    row = db.query(AdminNotification).filter(AdminNotification.id == notification_id).first()
    if not row:
        return {"message": "not_found"}

    if row.seen_at is None:
        row.seen_at = datetime.utcnow()
        row.seen_by_user_id = current_user.id
        db.commit()

    return {"message": "ok"}


@router.post("/notifications/mark-all-seen", response_model=dict)
def mark_all_notifications_seen(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_admin(current_user)

    now_utc = datetime.utcnow()
    (
        db.query(AdminNotification)
        .filter(AdminNotification.seen_at.is_(None))
        .update(
            {"seen_at": now_utc, "seen_by_user_id": current_user.id},
            synchronize_session=False,
        )
    )
    db.commit()
    return {"message": "ok"}
