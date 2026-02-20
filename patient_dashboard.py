# from __future__ import annotations

# import os
# from datetime import datetime, date, time, timedelta
# from typing import Any, Dict, List, Optional

# from fastapi import APIRouter, Depends, HTTPException, Request
# from pydantic import BaseModel
# from sqlalchemy import (
#     Column,
#     Integer,
#     Date,
#     DateTime,
#     ForeignKey,
#     String,
#     UniqueConstraint,
#     Text,
# )
# from sqlalchemy.orm import Session, relationship
# from sqlalchemy.exc import IntegrityError

# from db import Base
# from auth import get_db, get_current_user, write_audit_log
# from user import User

# from assignments import QuestionnaireAssignment

# # ✅ Flow engine models
# from flows import QuestionnaireFlow, FlowNode, FlowNodeOption, FlowNodeType

# try:
#     from zoneinfo import ZoneInfo
#     from zoneinfo import ZoneInfoNotFoundError
# except Exception:
#     ZoneInfo = None  # type: ignore
#     ZoneInfoNotFoundError = Exception  # type: ignore


# router = APIRouter(prefix="/patient", tags=["Patient Dashboard"])


# # -------------------------
# # Status constants
# # -------------------------
# class CheckinStatus:
#     NOT_STARTED = "NOT_STARTED"
#     IN_PROGRESS = "IN_PROGRESS"
#     COMPLETED = "COMPLETED"


# # -------------------------
# # Model: daily instance
# # -------------------------
# class QuestionnaireInstance(Base):
#     __tablename__ = "questionnaire_instances"
#     __table_args__ = (
#         UniqueConstraint("assignment_id", "scheduled_for", name="uq_instance_assignment_day"),
#     )

#     id = Column(Integer, primary_key=True)

#     patient_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
#     assignment_id = Column(Integer, ForeignKey("questionnaire_assignments.id"), nullable=False, index=True)

#     # ✅ Flow FK
#     flow_id = Column(Integer, ForeignKey("questionnaire_flows.id"), nullable=False, index=True)

#     scheduled_for = Column(Date, nullable=False, index=True)
#     status = Column(String(20), default=CheckinStatus.NOT_STARTED, nullable=False)

#     created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
#     submitted_at = Column(DateTime, nullable=True)

#     patient = relationship("User", foreign_keys=[patient_id])
#     assignment = relationship("QuestionnaireAssignment", foreign_keys=[assignment_id])
#     flow = relationship("QuestionnaireFlow", foreign_keys=[flow_id])


# # -------------------------
# # Model: answers per instance
# # node_id -> flow_nodes.id
# # option_id -> flow_node_options.id
# # -------------------------
# class QuestionnaireAnswer(Base):
#     __tablename__ = "questionnaire_answers"
#     __table_args__ = (
#         UniqueConstraint("instance_id", "node_id", name="uq_answer_instance_node"),
#     )

#     id = Column(Integer, primary_key=True)

#     instance_id = Column(Integer, ForeignKey("questionnaire_instances.id"), nullable=False, index=True)
#     patient_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

#     flow_id = Column(Integer, ForeignKey("questionnaire_flows.id"), nullable=False, index=True)
#     node_id = Column(Integer, ForeignKey("flow_nodes.id"), nullable=False, index=True)

#     option_id = Column(Integer, ForeignKey("flow_node_options.id"), nullable=True)
#     value_text = Column(Text, nullable=True)

#     created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
#     updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


# # -------------------------
# # Schemas: dashboard
# # -------------------------
# class DueItem(BaseModel):
#     assignment_id: int
#     flow_id: int
#     flow_name: str
#     status: str
#     instance_id: Optional[int] = None


# class DashboardOut(BaseModel):
#     cutoff_time: str
#     today_status: str  # DUE / COMPLETED / NO_CHECKIN / MISSED
#     time_left_seconds: int
#     missed_count: int
#     due_today: List[DueItem]


# class StartIn(BaseModel):
#     assignment_id: int


# class StartOut(BaseModel):
#     instance_id: int


# # -------------------------
# # Schemas: flow node navigation (Option A)
# # -------------------------
# class NodeOptionOut(BaseModel):
#     id: int
#     display_order: int
#     label: str
#     value: str
#     severity: str
#     seriousness_points: int
#     next_node_key: Optional[str] = None


# class NodeOut(BaseModel):
#     node_key: str
#     node_type: str  # QUESTION/MESSAGE/ALERT
#     title: Optional[str] = None
#     body_text: str
#     help_text: Optional[str] = None
#     ui_ack_required: bool
#     alert_severity: Optional[str] = None
#     notify_admin: bool

#     default_next_node_key: Optional[str] = None
#     auto_next_node_key: Optional[str] = None

#     options: List[NodeOptionOut] = []


# class NodeAnswerIn(BaseModel):
#     option_id: Optional[int] = None
#     value_text: Optional[str] = None


# class NodeAnswerOut(BaseModel):
#     instance_id: int
#     node_key: str
#     next_node_key: str  # node_key or "END"


# class CheckinMetaOut(BaseModel):
#     instance_id: int
#     status: str
#     scheduled_for: str
#     flow: Dict[str, Any]  # includes start_node_key for frontend


# class CompleteOut(BaseModel):
#     message: str
#     instance_id: int
#     status: str


# # -------------------------
# # Schemas: checkins list
# # -------------------------
# class CheckinRowOut(BaseModel):
#     instance_id: int
#     assignment_id: int
#     flow_id: int
#     flow_name: str
#     scheduled_for: str
#     status: str
#     submitted_at: Optional[str] = None
#     total_score: int


# class AttemptRowOut(BaseModel):
#     instance_id: int
#     flow_id: int
#     flow_name: str
#     scheduled_for: str
#     submitted_at: Optional[str] = None
#     total_score: int


# class AttemptsListOut(BaseModel):
#     total: int
#     items: List[AttemptRowOut]


# # -------------------------
# # Helpers
# # -------------------------
# def _get_tz():
#     tz_key = os.getenv("HOSPITAL_TIMEZONE", "Europe/Lisbon")
#     if ZoneInfo is None:
#         return None
#     try:
#         return ZoneInfo(tz_key)
#     except ZoneInfoNotFoundError:
#         return ZoneInfo("UTC")


# def _local_now() -> datetime:
#     tz = _get_tz()
#     fake = os.getenv("DEV_NOW") if os.getenv("DEV_TIME_TRAVEL") == "1" else None
#     if fake:
#         dt = datetime.fromisoformat(fake)
#         return dt.replace(tzinfo=tz) if tz else dt
#     return datetime.now(tz=tz) if tz else datetime.utcnow()


# def _local_today() -> date:
#     return _local_now().date()


# def _end_of_day_dt(day: date) -> datetime:
#     tz = _get_tz()
#     eod = datetime.combine(day, time(23, 59, 59))
#     return eod.replace(tzinfo=tz) if tz else eod


# def _is_patient(user: User) -> bool:
#     roles = {r.name for r in getattr(user, "roles", [])}
#     return ("PATIENT" in roles) or ("PATIENT_INTERNAL" in roles)


# def _require_patient(user: User):
#     if not _is_patient(user):
#         raise HTTPException(status_code=403, detail="Patient access required")


# def _days_in_range(start: date, end: date) -> int:
#     if end < start:
#         return 0
#     return (end.toordinal() - start.toordinal()) + 1


# def _compute_missed(
#     db: Session,
#     patient_id: int,
#     todays_active_assignments: List[QuestionnaireAssignment],
#     today: date,
# ) -> int:
#     yesterday = today - timedelta(days=1)

#     expected = 0
#     for a in todays_active_assignments:
#         if a.start_date > yesterday:
#             continue
#         end = min(a.end_date, yesterday)
#         expected += _days_in_range(a.start_date, end)

#     completed = (
#         db.query(QuestionnaireInstance)
#         .filter(
#             QuestionnaireInstance.patient_id == patient_id,
#             QuestionnaireInstance.status == CheckinStatus.COMPLETED,
#             QuestionnaireInstance.scheduled_for <= yesterday,
#         )
#         .count()
#     )
#     return max(0, expected - completed)


# def _get_flow(db: Session, flow_id: int) -> QuestionnaireFlow:
#     flow = (
#         db.query(QuestionnaireFlow)
#         .filter(
#             QuestionnaireFlow.id == flow_id,
#             QuestionnaireFlow.is_deleted == False,  # noqa: E712
#         )
#         .first()
#     )
#     if not flow:
#         raise HTTPException(status_code=404, detail="Flow not found")
#     return flow


# def _get_node_by_key(db: Session, *, flow_id: int, node_key: str) -> FlowNode:
#     node = (
#         db.query(FlowNode)
#         .filter(
#             FlowNode.flow_id == flow_id,
#             FlowNode.node_key == node_key,
#         )
#         .first()
#     )
#     if not node:
#         raise HTTPException(status_code=404, detail=f"Node '{node_key}' not found in this flow")
#     return node


# def _get_node_options(db: Session, node_id: int) -> List[FlowNodeOption]:
#     return (
#         db.query(FlowNodeOption)
#         .filter(FlowNodeOption.node_id == node_id)
#         .order_by(FlowNodeOption.display_order.asc())
#         .all()
#     )


# def _validate_option_belongs_to_node(db: Session, *, node_id: int, option_id: int) -> FlowNodeOption:
#     row = (
#         db.query(FlowNodeOption)
#         .filter(
#             FlowNodeOption.id == option_id,
#             FlowNodeOption.node_id == node_id,
#         )
#         .first()
#     )
#     if not row:
#         raise HTTPException(status_code=400, detail=f"option_id {option_id} does not belong to node_id {node_id}")
#     return row


# def _compute_instance_total_score(db: Session, *, instance_id: int, patient_id: int) -> int:
#     option_ids = [
#         r[0]
#         for r in db.query(QuestionnaireAnswer.option_id)
#         .filter(
#             QuestionnaireAnswer.instance_id == instance_id,
#             QuestionnaireAnswer.patient_id == patient_id,
#             QuestionnaireAnswer.option_id.isnot(None),
#         )
#         .all()
#         if r and r[0] is not None
#     ]
#     if not option_ids:
#         return 0

#     pts = db.query(FlowNodeOption.seriousness_points).filter(FlowNodeOption.id.in_(option_ids)).all()
#     return sum(int(p[0] or 0) for p in pts)


# def _add_admin_submission_notification_safe(db: Session, *, patient: User, instance: QuestionnaireInstance):
#     try:
#         from admin_monitoring import AdminNotification

#         notif = AdminNotification(
#             type="NEW_SUBMISSION",
#             severity="INFO",
#             patient_id=patient.id,
#             instance_id=instance.id,
#             message=f"New submission from {patient.name}",
#         )
#         db.add(notif)
#     except Exception:
#         pass


# # ============================================================
# # Routes
# # ============================================================

# @router.get("/dashboard", response_model=DashboardOut)
# def patient_dashboard(
#     db: Session = Depends(get_db),
#     current_user: User = Depends(get_current_user),
# ):
#     _require_patient(current_user)

#     now = _local_now()
#     today = _local_today()
#     cutoff_str = "23:59"

#     assignments = (
#         db.query(QuestionnaireAssignment)
#         .filter(
#             QuestionnaireAssignment.patient_id == current_user.id,
#             QuestionnaireAssignment.is_active == True,  # noqa: E712
#             QuestionnaireAssignment.start_date <= today,
#             QuestionnaireAssignment.end_date >= today,
#         )
#         .all()
#     )

#     if not assignments:
#         return DashboardOut(
#             cutoff_time=cutoff_str,
#             today_status="NO_CHECKIN",
#             time_left_seconds=0,
#             missed_count=0,
#             due_today=[],
#         )

#     due_today: List[DueItem] = []
#     all_completed = True

#     for a in assignments:
#         flow = _get_flow(db, a.flow_id)

#         inst = (
#             db.query(QuestionnaireInstance)
#             .filter(
#                 QuestionnaireInstance.assignment_id == a.id,
#                 QuestionnaireInstance.scheduled_for == today,
#             )
#             .first()
#         )

#         status = inst.status if inst else CheckinStatus.NOT_STARTED
#         if status != CheckinStatus.COMPLETED:
#             all_completed = False

#         due_today.append(
#             DueItem(
#                 assignment_id=a.id,
#                 flow_id=a.flow_id,
#                 flow_name=flow.name,
#                 status=status,
#                 instance_id=inst.id if inst else None,
#             )
#         )

#     missed_count = _compute_missed(db, current_user.id, assignments, today)

#     if all_completed:
#         return DashboardOut(
#             cutoff_time=cutoff_str,
#             today_status="COMPLETED",
#             time_left_seconds=0,
#             missed_count=missed_count,
#             due_today=due_today,
#         )

#     eod = _end_of_day_dt(today)
#     secs = max(0, int((eod - now).total_seconds()))

#     return DashboardOut(
#         cutoff_time=cutoff_str,
#         today_status="DUE",
#         time_left_seconds=secs,
#         missed_count=missed_count,
#         due_today=due_today,
#     )


# @router.post("/checkins/start", response_model=StartOut)
# def start_today_checkin(
#     payload: StartIn,
#     request: Request,
#     db: Session = Depends(get_db),
#     current_user: User = Depends(get_current_user),
# ):
#     _require_patient(current_user)

#     today = _local_today()

#     a = (
#         db.query(QuestionnaireAssignment)
#         .filter(
#             QuestionnaireAssignment.id == payload.assignment_id,
#             QuestionnaireAssignment.patient_id == current_user.id,
#             QuestionnaireAssignment.is_active == True,  # noqa: E712
#             QuestionnaireAssignment.start_date <= today,
#             QuestionnaireAssignment.end_date >= today,
#         )
#         .first()
#     )
#     if not a:
#         raise HTTPException(status_code=404, detail="Assignment not found or not active for today")

#     inst = (
#         db.query(QuestionnaireInstance)
#         .filter(
#             QuestionnaireInstance.assignment_id == a.id,
#             QuestionnaireInstance.scheduled_for == today,
#         )
#         .first()
#     )

#     if inst and inst.status == CheckinStatus.COMPLETED:
#         return StartOut(instance_id=inst.id)

#     if not inst:
#         inst = QuestionnaireInstance(
#             patient_id=current_user.id,
#             assignment_id=a.id,
#             flow_id=a.flow_id,
#             scheduled_for=today,
#             status=CheckinStatus.IN_PROGRESS,
#         )
#         db.add(inst)
#         db.commit()
#         db.refresh(inst)
#     else:
#         if inst.status == CheckinStatus.NOT_STARTED:
#             inst.status = CheckinStatus.IN_PROGRESS
#             db.commit()

#     write_audit_log(db, "PATIENT_CHECKIN_STARTED", user_id=current_user.id, request=request)
#     return StartOut(instance_id=inst.id)


# # ✅ Meta endpoint: now includes start_node_key (needed for frontend Option A)
# @router.get("/checkins/{instance_id}", response_model=CheckinMetaOut)
# def get_checkin_meta(
#     instance_id: int,
#     db: Session = Depends(get_db),
#     current_user: User = Depends(get_current_user),
# ):
#     _require_patient(current_user)

#     inst = (
#         db.query(QuestionnaireInstance)
#         .filter(
#             QuestionnaireInstance.id == instance_id,
#             QuestionnaireInstance.patient_id == current_user.id,
#         )
#         .first()
#     )
#     if not inst:
#         raise HTTPException(status_code=404, detail="Check-in instance not found")

#     flow = _get_flow(db, inst.flow_id)

#     return CheckinMetaOut(
#         instance_id=inst.id,
#         status=inst.status,
#         scheduled_for=inst.scheduled_for.isoformat(),
#         flow={
#             "id": flow.id,
#             "name": flow.name,
#             "flow_type": str(flow.flow_type),
#             "start_node_key": flow.start_node_key,  # ✅ critical
#         },
#     )


# @router.get("/checkins/{instance_id}/node/{node_key}", response_model=NodeOut)
# def get_checkin_node(
#     instance_id: int,
#     node_key: str,
#     db: Session = Depends(get_db),
#     current_user: User = Depends(get_current_user),
# ):
#     _require_patient(current_user)

#     inst = (
#         db.query(QuestionnaireInstance)
#         .filter(
#             QuestionnaireInstance.id == instance_id,
#             QuestionnaireInstance.patient_id == current_user.id,
#         )
#         .first()
#     )
#     if not inst:
#         raise HTTPException(status_code=404, detail="Check-in instance not found")

#     node = _get_node_by_key(db, flow_id=inst.flow_id, node_key=node_key)

#     opts_out: List[NodeOptionOut] = []
#     if node.node_type == FlowNodeType.QUESTION:
#         opts = _get_node_options(db, node.id)
#         opts_out = [
#             NodeOptionOut(
#                 id=o.id,
#                 display_order=o.display_order,
#                 label=o.label,
#                 value=o.value,
#                 severity=o.severity.value if hasattr(o.severity, "value") else str(o.severity),
#                 seriousness_points=int(getattr(o, "seriousness_points", 0) or 0),
#                 next_node_key=o.next_node_key,
#             )
#             for o in opts
#         ]

#     return NodeOut(
#         node_key=node.node_key,
#         node_type=node.node_type.value,
#         title=node.title,
#         body_text=node.body_text,
#         help_text=node.help_text,
#         ui_ack_required=bool(node.ui_ack_required),
#         alert_severity=node.alert_severity.value if node.alert_severity else None,
#         notify_admin=bool(node.notify_admin),
#         default_next_node_key=node.default_next_node_key,
#         auto_next_node_key=node.auto_next_node_key,
#         options=opts_out,
#     )


# @router.post("/checkins/{instance_id}/node/{node_key}/answer", response_model=NodeAnswerOut)
# def answer_checkin_node(
#     instance_id: int,
#     node_key: str,
#     payload: NodeAnswerIn,
#     request: Request,
#     db: Session = Depends(get_db),
#     current_user: User = Depends(get_current_user),
# ):
#     _require_patient(current_user)

#     today = _local_today()

#     inst = (
#         db.query(QuestionnaireInstance)
#         .filter(
#             QuestionnaireInstance.id == instance_id,
#             QuestionnaireInstance.patient_id == current_user.id,
#         )
#         .first()
#     )
#     if not inst:
#         raise HTTPException(status_code=404, detail="Check-in instance not found")

#     if inst.scheduled_for != today:
#         raise HTTPException(status_code=403, detail="You can only answer a check-in on its scheduled day")

#     if inst.status == CheckinStatus.COMPLETED:
#         raise HTTPException(status_code=400, detail="Check-in already completed")

#     node = _get_node_by_key(db, flow_id=inst.flow_id, node_key=node_key)

#     chosen_opt: Optional[FlowNodeOption] = None
#     if node.node_type == FlowNodeType.QUESTION:
#         if payload.option_id is None:
#             raise HTTPException(status_code=400, detail="option_id is required for QUESTION nodes")
#         chosen_opt = _validate_option_belongs_to_node(db, node_id=node.id, option_id=payload.option_id)
#     else:
#         if payload.option_id is not None:
#             raise HTTPException(status_code=400, detail="option_id not allowed for MESSAGE/ALERT nodes")

#     row = (
#         db.query(QuestionnaireAnswer)
#         .filter(
#             QuestionnaireAnswer.instance_id == inst.id,
#             QuestionnaireAnswer.node_id == node.id,
#         )
#         .first()
#     )

#     if not row:
#         row = QuestionnaireAnswer(
#             instance_id=inst.id,
#             patient_id=current_user.id,
#             flow_id=inst.flow_id,
#             node_id=node.id,
#             option_id=payload.option_id,
#             value_text=payload.value_text,
#         )
#         db.add(row)
#     else:
#         row.option_id = payload.option_id
#         row.value_text = payload.value_text

#     next_key = "END"
#     if node.node_type == FlowNodeType.QUESTION:
#         if chosen_opt and chosen_opt.next_node_key:
#             next_key = chosen_opt.next_node_key
#         elif node.default_next_node_key:
#             next_key = node.default_next_node_key
#     else:
#         next_key = node.auto_next_node_key or "END"

#     try:
#         db.commit()
#     except IntegrityError:
#         db.rollback()
#         raise HTTPException(status_code=409, detail="Duplicate answer detected. Please retry.")

#     write_audit_log(
#         db,
#         "PATIENT_NODE_ANSWERED",
#         user_id=current_user.id,
#         request=request,
#         details=f"instance_id={inst.id}, node_key={node_key}, next={next_key}",
#     )

#     return NodeAnswerOut(instance_id=inst.id, node_key=node_key, next_node_key=next_key)


# @router.post("/checkins/{instance_id}/complete", response_model=CompleteOut)
# def complete_checkin(
#     instance_id: int,
#     request: Request,
#     db: Session = Depends(get_db),
#     current_user: User = Depends(get_current_user),
# ):
#     _require_patient(current_user)

#     today = _local_today()

#     inst = (
#         db.query(QuestionnaireInstance)
#         .filter(
#             QuestionnaireInstance.id == instance_id,
#             QuestionnaireInstance.patient_id == current_user.id,
#         )
#         .first()
#     )
#     if not inst:
#         raise HTTPException(status_code=404, detail="Check-in instance not found")

#     if inst.scheduled_for != today:
#         raise HTTPException(status_code=403, detail="You can only complete a check-in on its scheduled day")

#     if inst.status == CheckinStatus.COMPLETED:
#         return CompleteOut(message="Already completed", instance_id=inst.id, status=inst.status)

#     inst.status = CheckinStatus.COMPLETED
#     inst.submitted_at = datetime.utcnow()

#     _add_admin_submission_notification_safe(db, patient=current_user, instance=inst)

#     db.commit()

#     write_audit_log(db, "PATIENT_CHECKIN_COMPLETED", user_id=current_user.id, request=request)
#     return CompleteOut(message="Completed", instance_id=inst.id, status=inst.status)


# @router.get("/checkins", response_model=List[CheckinRowOut])
# def list_my_checkins(
#     db: Session = Depends(get_db),
#     current_user: User = Depends(get_current_user),
#     limit: int = 100,
# ):
#     _require_patient(current_user)

#     rows = (
#         db.query(QuestionnaireInstance)
#         .filter(QuestionnaireInstance.patient_id == current_user.id)
#         .order_by(QuestionnaireInstance.scheduled_for.desc(), QuestionnaireInstance.id.desc())
#         .limit(min(max(limit, 1), 200))
#         .all()
#     )

#     out: List[CheckinRowOut] = []
#     for inst in rows:
#         flow = _get_flow(db, inst.flow_id)
#         total_score = _compute_instance_total_score(db, instance_id=inst.id, patient_id=current_user.id)

#         out.append(
#             CheckinRowOut(
#                 instance_id=inst.id,
#                 assignment_id=inst.assignment_id,
#                 flow_id=inst.flow_id,
#                 flow_name=flow.name,
#                 scheduled_for=inst.scheduled_for.isoformat(),
#                 status=inst.status,
#                 submitted_at=inst.submitted_at.isoformat() if inst.submitted_at else None,
#                 total_score=total_score,
#             )
#         )

#     return out


# @router.get("/attempts", response_model=AttemptsListOut)
# def list_my_attempts(
#     db: Session = Depends(get_db),
#     current_user: User = Depends(get_current_user),
#     skip: int = 0,
#     limit: int = 50,
# ):
#     _require_patient(current_user)

#     base = (
#         db.query(QuestionnaireInstance)
#         .filter(
#             QuestionnaireInstance.patient_id == current_user.id,
#             QuestionnaireInstance.status == CheckinStatus.COMPLETED,
#         )
#     )

#     total = base.count()

#     instances = (
#         base.order_by(QuestionnaireInstance.scheduled_for.desc(), QuestionnaireInstance.id.desc())
#         .offset(skip)
#         .limit(min(limit, 200))
#         .all()
#     )

#     items: List[AttemptRowOut] = []
#     for inst in instances:
#         flow = _get_flow(db, inst.flow_id)
#         total_score = _compute_instance_total_score(db, instance_id=inst.id, patient_id=current_user.id)

#         items.append(
#             AttemptRowOut(
#                 instance_id=inst.id,
#                 flow_id=inst.flow_id,
#                 flow_name=flow.name,
#                 scheduled_for=inst.scheduled_for.isoformat(),
#                 submitted_at=inst.submitted_at.isoformat() if inst.submitted_at else None,
#                 total_score=total_score,
#             )
#         )

#     return AttemptsListOut(total=total, items=items)

from __future__ import annotations

import os
from datetime import datetime, date, time, timedelta
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import (
    Column,
    Integer,
    Date,
    DateTime,
    ForeignKey,
    String,
    UniqueConstraint,
    Text,
)
from sqlalchemy.orm import Session, relationship
from sqlalchemy.exc import IntegrityError

from db import Base
from auth import get_db, get_current_user, write_audit_log
from user import User

from assignments import QuestionnaireAssignment

# ✅ Flow engine models
from flows import QuestionnaireFlow, FlowNode, FlowNodeOption, FlowNodeType

try:
    from zoneinfo import ZoneInfo
    from zoneinfo import ZoneInfoNotFoundError
except Exception:
    ZoneInfo = None  # type: ignore
    ZoneInfoNotFoundError = Exception  # type: ignore


router = APIRouter(prefix="/patient", tags=["Patient Dashboard"])


# -------------------------
# Status constants
# -------------------------
class CheckinStatus:
    NOT_STARTED = "NOT_STARTED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"


# -------------------------
# Model: daily instance
# -------------------------
class QuestionnaireInstance(Base):
    __tablename__ = "questionnaire_instances"
    __table_args__ = (
        UniqueConstraint("assignment_id", "scheduled_for", name="uq_instance_assignment_day"),
    )

    id = Column(Integer, primary_key=True)

    patient_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    assignment_id = Column(Integer, ForeignKey("questionnaire_assignments.id"), nullable=False, index=True)

    # ✅ Flow FK
    flow_id = Column(Integer, ForeignKey("questionnaire_flows.id"), nullable=False, index=True)

    scheduled_for = Column(Date, nullable=False, index=True)
    status = Column(String(20), default=CheckinStatus.NOT_STARTED, nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    submitted_at = Column(DateTime, nullable=True)

    patient = relationship("User", foreign_keys=[patient_id])
    assignment = relationship("QuestionnaireAssignment", foreign_keys=[assignment_id])
    flow = relationship("QuestionnaireFlow", foreign_keys=[flow_id])


# -------------------------
# Model: answers per instance
# node_id -> flow_nodes.id
# option_id -> flow_node_options.id
# -------------------------
class QuestionnaireAnswer(Base):
    __tablename__ = "questionnaire_answers"
    __table_args__ = (
        UniqueConstraint("instance_id", "node_id", name="uq_answer_instance_node"),
    )

    id = Column(Integer, primary_key=True)

    instance_id = Column(Integer, ForeignKey("questionnaire_instances.id"), nullable=False, index=True)
    patient_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    flow_id = Column(Integer, ForeignKey("questionnaire_flows.id"), nullable=False, index=True)
    node_id = Column(Integer, ForeignKey("flow_nodes.id"), nullable=False, index=True)

    option_id = Column(Integer, ForeignKey("flow_node_options.id"), nullable=True)
    value_text = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


# -------------------------
# Schemas: dashboard
# -------------------------
class DueItem(BaseModel):
    assignment_id: int
    flow_id: int
    flow_name: str
    status: str
    instance_id: Optional[int] = None


class DashboardOut(BaseModel):
    cutoff_time: str
    today_status: str  # DUE / COMPLETED / NO_CHECKIN / MISSED
    time_left_seconds: int
    missed_count: int
    due_today: List[DueItem]


class StartIn(BaseModel):
    assignment_id: int


class StartOut(BaseModel):
    instance_id: int


# -------------------------
# Schemas: flow node navigation (Option A)
# -------------------------
class NodeOptionOut(BaseModel):
    id: int
    display_order: int
    label: str
    value: str
    severity: str
    seriousness_points: int
    next_node_key: Optional[str] = None


class NodeOut(BaseModel):
    node_key: str
    node_type: str  # QUESTION/MESSAGE/ALERT
    title: Optional[str] = None
    body_text: str
    help_text: Optional[str] = None
    ui_ack_required: bool
    alert_severity: Optional[str] = None
    notify_admin: bool

    default_next_node_key: Optional[str] = None
    auto_next_node_key: Optional[str] = None

    options: List[NodeOptionOut] = []


class NodeAnswerIn(BaseModel):
    option_id: Optional[int] = None
    value_text: Optional[str] = None


class NodeAnswerOut(BaseModel):
    instance_id: int
    node_key: str
    next_node_key: str  # node_key or "END"


class CheckinMetaOut(BaseModel):
    instance_id: int
    status: str
    scheduled_for: str
    flow: Dict[str, Any]  # includes start_node_key for frontend


class CompleteOut(BaseModel):
    message: str
    instance_id: int
    status: str


# -------------------------
# Schemas: checkins list
# -------------------------
class CheckinRowOut(BaseModel):
    instance_id: int
    assignment_id: int
    flow_id: int
    flow_name: str
    scheduled_for: str
    status: str
    submitted_at: Optional[str] = None
    total_score: int


class AttemptRowOut(BaseModel):
    instance_id: int
    flow_id: int
    flow_name: str
    scheduled_for: str
    submitted_at: Optional[str] = None
    total_score: int


class AttemptsListOut(BaseModel):
    total: int
    items: List[AttemptRowOut]


class AttemptDetailItem(BaseModel):
    node_key: str
    question: str
    answer: Optional[str]


class AttemptDetailOut(BaseModel):
    instance_id: int
    flow_name: str
    submitted_at: Optional[str]
    items: List[AttemptDetailItem]



# -------------------------
# Helpers
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
    tz = _get_tz()
    fake = os.getenv("DEV_NOW") if os.getenv("DEV_TIME_TRAVEL") == "1" else None
    if fake:
        dt = datetime.fromisoformat(fake)
        return dt.replace(tzinfo=tz) if tz else dt
    return datetime.now(tz=tz) if tz else datetime.utcnow()


def _local_today() -> date:
    return _local_now().date()


def _end_of_day_dt(day: date) -> datetime:
    tz = _get_tz()
    eod = datetime.combine(day, time(23, 59, 59))
    return eod.replace(tzinfo=tz) if tz else eod


def _is_patient(user: User) -> bool:
    roles = {r.name for r in getattr(user, "roles", [])}
    return ("PATIENT" in roles) or ("PATIENT_INTERNAL" in roles)


def _require_patient(user: User):
    if not _is_patient(user):
        raise HTTPException(status_code=403, detail="Patient access required")


def _days_in_range(start: date, end: date) -> int:
    if end < start:
        return 0
    return (end.toordinal() - start.toordinal()) + 1


def _compute_missed(
    db: Session,
    patient_id: int,
    todays_active_assignments: List[QuestionnaireAssignment],
    today: date,
) -> int:
    yesterday = today - timedelta(days=1)

    expected = 0
    for a in todays_active_assignments:
        if a.start_date > yesterday:
            continue
        end = min(a.end_date, yesterday)
        expected += _days_in_range(a.start_date, end)

    completed = (
        db.query(QuestionnaireInstance)
        .filter(
            QuestionnaireInstance.patient_id == patient_id,
            QuestionnaireInstance.status == CheckinStatus.COMPLETED,
            QuestionnaireInstance.scheduled_for <= yesterday,
        )
        .count()
    )
    return max(0, expected - completed)


def _get_flow(db: Session, flow_id: int) -> QuestionnaireFlow:
    flow = (
        db.query(QuestionnaireFlow)
        .filter(
            QuestionnaireFlow.id == flow_id,
            QuestionnaireFlow.is_deleted == False,  # noqa: E712
        )
        .first()
    )
    if not flow:
        raise HTTPException(status_code=404, detail="Flow not found")
    return flow


def _get_node_by_key(db: Session, *, flow_id: int, node_key: str) -> FlowNode:
    node = (
        db.query(FlowNode)
        .filter(
            FlowNode.flow_id == flow_id,
            FlowNode.node_key == node_key,
        )
        .first()
    )
    if not node:
        raise HTTPException(status_code=404, detail=f"Node '{node_key}' not found in this flow")
    return node


def _get_node_options(db: Session, node_id: int) -> List[FlowNodeOption]:
    return (
        db.query(FlowNodeOption)
        .filter(FlowNodeOption.node_id == node_id)
        .order_by(FlowNodeOption.display_order.asc())
        .all()
    )


def _validate_option_belongs_to_node(db: Session, *, node_id: int, option_id: int) -> FlowNodeOption:
    row = (
        db.query(FlowNodeOption)
        .filter(
            FlowNodeOption.id == option_id,
            FlowNodeOption.node_id == node_id,
        )
        .first()
    )
    if not row:
        raise HTTPException(status_code=400, detail=f"option_id {option_id} does not belong to node_id {node_id}")
    return row


def _compute_instance_total_score(db: Session, *, instance_id: int, patient_id: int) -> int:
    option_ids = [
        r[0]
        for r in db.query(QuestionnaireAnswer.option_id)
        .filter(
            QuestionnaireAnswer.instance_id == instance_id,
            QuestionnaireAnswer.patient_id == patient_id,
            QuestionnaireAnswer.option_id.isnot(None),
        )
        .all()
        if r and r[0] is not None
    ]
    if not option_ids:
        return 0

    pts = db.query(FlowNodeOption.seriousness_points).filter(FlowNodeOption.id.in_(option_ids)).all()
    return sum(int(p[0] or 0) for p in pts)


def _add_admin_submission_notification_safe(db: Session, *, patient: User, instance: QuestionnaireInstance):
    try:
        from admin_monitoring import AdminNotification

        notif = AdminNotification(
            type="NEW_SUBMISSION",
            severity="INFO",
            patient_id=patient.id,
            instance_id=instance.id,
            message=f"New submission from {patient.name}",
        )
        db.add(notif)
    except Exception:
        pass


# ================================
# ✅ NEW: Category chaining helpers
# ================================
def _get_first_root_node_key_for_category(db: Session, *, flow_id: int, category: int) -> Optional[str]:
    row = (
        db.query(FlowNode)
        .filter(
            FlowNode.flow_id == flow_id,
            FlowNode.category == category,
            FlowNode.parent_node_key.is_(None),
        )
        .order_by(FlowNode.display_order.asc(), FlowNode.id.asc())
        .first()
    )
    return row.node_key if row else None


def _get_next_category_start(db: Session, *, flow_id: int, current_category: int) -> Optional[str]:
    # Fixed categories: 1 -> 2
    if current_category == 1:
        return _get_first_root_node_key_for_category(db, flow_id=flow_id, category=2)
    return None


# ============================================================
# Routes
# ============================================================

@router.get("/dashboard", response_model=DashboardOut)
def patient_dashboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_patient(current_user)

    now = _local_now()
    today = _local_today()
    cutoff_str = "23:59"

    assignments = (
        db.query(QuestionnaireAssignment)
        .filter(
            QuestionnaireAssignment.patient_id == current_user.id,
            QuestionnaireAssignment.is_active == True,  # noqa: E712
            QuestionnaireAssignment.start_date <= today,
            QuestionnaireAssignment.end_date >= today,
        )
        .all()
    )

    if not assignments:
        return DashboardOut(
            cutoff_time=cutoff_str,
            today_status="NO_CHECKIN",
            time_left_seconds=0,
            missed_count=0,
            due_today=[],
        )

    due_today: List[DueItem] = []
    all_completed = True

    for a in assignments:
        flow = _get_flow(db, a.flow_id)

        inst = (
            db.query(QuestionnaireInstance)
            .filter(
                QuestionnaireInstance.assignment_id == a.id,
                QuestionnaireInstance.scheduled_for == today,
            )
            .first()
        )

        status = inst.status if inst else CheckinStatus.NOT_STARTED
        if status != CheckinStatus.COMPLETED:
            all_completed = False

        due_today.append(
            DueItem(
                assignment_id=a.id,
                flow_id=a.flow_id,
                flow_name=flow.name,
                status=status,
                instance_id=inst.id if inst else None,
            )
        )

    missed_count = _compute_missed(db, current_user.id, assignments, today)

    if all_completed:
        return DashboardOut(
            cutoff_time=cutoff_str,
            today_status="COMPLETED",
            time_left_seconds=0,
            missed_count=missed_count,
            due_today=due_today,
        )

    eod = _end_of_day_dt(today)
    secs = max(0, int((eod - now).total_seconds()))

    return DashboardOut(
        cutoff_time=cutoff_str,
        today_status="DUE",
        time_left_seconds=secs,
        missed_count=missed_count,
        due_today=due_today,
    )


@router.post("/checkins/start", response_model=StartOut)
def start_today_checkin(
    payload: StartIn,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_patient(current_user)

    today = _local_today()

    a = (
        db.query(QuestionnaireAssignment)
        .filter(
            QuestionnaireAssignment.id == payload.assignment_id,
            QuestionnaireAssignment.patient_id == current_user.id,
            QuestionnaireAssignment.is_active == True,  # noqa: E712
            QuestionnaireAssignment.start_date <= today,
            QuestionnaireAssignment.end_date >= today,
        )
        .first()
    )
    if not a:
        raise HTTPException(status_code=404, detail="Assignment not found or not active for today")

    inst = (
        db.query(QuestionnaireInstance)
        .filter(
            QuestionnaireInstance.assignment_id == a.id,
            QuestionnaireInstance.scheduled_for == today,
        )
        .first()
    )

    if inst and inst.status == CheckinStatus.COMPLETED:
        return StartOut(instance_id=inst.id)

    if not inst:
        inst = QuestionnaireInstance(
            patient_id=current_user.id,
            assignment_id=a.id,
            flow_id=a.flow_id,
            scheduled_for=today,
            status=CheckinStatus.IN_PROGRESS,
        )
        db.add(inst)
        db.commit()
        db.refresh(inst)
    else:
        if inst.status == CheckinStatus.NOT_STARTED:
            inst.status = CheckinStatus.IN_PROGRESS
            db.commit()

    write_audit_log(db, "PATIENT_CHECKIN_STARTED", user_id=current_user.id, request=request)
    return StartOut(instance_id=inst.id)


@router.get("/checkins/{instance_id}", response_model=CheckinMetaOut)
def get_checkin_meta(
    instance_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_patient(current_user)

    inst = (
        db.query(QuestionnaireInstance)
        .filter(
            QuestionnaireInstance.id == instance_id,
            QuestionnaireInstance.patient_id == current_user.id,
        )
        .first()
    )
    if not inst:
        raise HTTPException(status_code=404, detail="Check-in instance not found")

    flow = _get_flow(db, inst.flow_id)

    return CheckinMetaOut(
        instance_id=inst.id,
        status=inst.status,
        scheduled_for=inst.scheduled_for.isoformat(),
        flow={
            "id": flow.id,
            "name": flow.name,
            "flow_type": str(flow.flow_type),
            "start_node_key": flow.start_node_key,
        },
    )


@router.get("/checkins/{instance_id}/node/{node_key}", response_model=NodeOut)
def get_checkin_node(
    instance_id: int,
    node_key: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_patient(current_user)

    inst = (
        db.query(QuestionnaireInstance)
        .filter(
            QuestionnaireInstance.id == instance_id,
            QuestionnaireInstance.patient_id == current_user.id,
        )
        .first()
    )
    if not inst:
        raise HTTPException(status_code=404, detail="Check-in instance not found")

    node = _get_node_by_key(db, flow_id=inst.flow_id, node_key=node_key)

    opts_out: List[NodeOptionOut] = []
    if node.node_type == FlowNodeType.QUESTION:
        opts = _get_node_options(db, node.id)
        opts_out = [
            NodeOptionOut(
                id=o.id,
                display_order=o.display_order,
                label=o.label,
                value=o.value,
                severity=o.severity.value if hasattr(o.severity, "value") else str(o.severity),
                seriousness_points=int(getattr(o, "seriousness_points", 0) or 0),
                next_node_key=o.next_node_key,
            )
            for o in opts
        ]

    return NodeOut(
        node_key=node.node_key,
        node_type=node.node_type.value,
        title=node.title,
        body_text=node.body_text,
        help_text=node.help_text,
        ui_ack_required=bool(node.ui_ack_required),
        alert_severity=node.alert_severity.value if node.alert_severity else None,
        notify_admin=bool(node.notify_admin),
        default_next_node_key=node.default_next_node_key,
        auto_next_node_key=node.auto_next_node_key,
        options=opts_out,
    )


@router.post("/checkins/{instance_id}/node/{node_key}/answer", response_model=NodeAnswerOut)
def answer_checkin_node(
    instance_id: int,
    node_key: str,
    payload: NodeAnswerIn,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_patient(current_user)

    today = _local_today()

    inst = (
        db.query(QuestionnaireInstance)
        .filter(
            QuestionnaireInstance.id == instance_id,
            QuestionnaireInstance.patient_id == current_user.id,
        )
        .first()
    )
    if not inst:
        raise HTTPException(status_code=404, detail="Check-in instance not found")

    if inst.scheduled_for != today:
        raise HTTPException(status_code=403, detail="You can only answer a check-in on its scheduled day")

    if inst.status == CheckinStatus.COMPLETED:
        raise HTTPException(status_code=400, detail="Check-in already completed")

    node = _get_node_by_key(db, flow_id=inst.flow_id, node_key=node_key)

    chosen_opt: Optional[FlowNodeOption] = None
    if node.node_type == FlowNodeType.QUESTION:
        if payload.option_id is None:
            raise HTTPException(status_code=400, detail="option_id is required for QUESTION nodes")
        chosen_opt = _validate_option_belongs_to_node(db, node_id=node.id, option_id=payload.option_id)
    else:
        if payload.option_id is not None:
            raise HTTPException(status_code=400, detail="option_id not allowed for MESSAGE/ALERT nodes")

    row = (
        db.query(QuestionnaireAnswer)
        .filter(
            QuestionnaireAnswer.instance_id == inst.id,
            QuestionnaireAnswer.node_id == node.id,
        )
        .first()
    )

    if not row:
        row = QuestionnaireAnswer(
            instance_id=inst.id,
            patient_id=current_user.id,
            flow_id=inst.flow_id,
            node_id=node.id,
            option_id=payload.option_id,
            value_text=payload.value_text,
        )
        db.add(row)
    else:
        row.option_id = payload.option_id
        row.value_text = payload.value_text

    next_key = "END"
    if node.node_type == FlowNodeType.QUESTION:
        if chosen_opt and chosen_opt.next_node_key:
            next_key = chosen_opt.next_node_key
        elif node.default_next_node_key:
            next_key = node.default_next_node_key
    else:
        next_key = node.auto_next_node_key or "END"

    # ✅ FIX: If this category ends, jump into the next category if it has a root node.
    if next_key == "END":
        nxt = _get_next_category_start(db, flow_id=inst.flow_id, current_category=int(getattr(node, "category", 1) or 1))
        if nxt:
            next_key = nxt

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Duplicate answer detected. Please retry.")

    write_audit_log(
        db,
        "PATIENT_NODE_ANSWERED",
        user_id=current_user.id,
        request=request,
        details=f"instance_id={inst.id}, node_key={node_key}, next={next_key}",
    )

    return NodeAnswerOut(instance_id=inst.id, node_key=node_key, next_node_key=next_key)


@router.post("/checkins/{instance_id}/complete", response_model=CompleteOut)
def complete_checkin(
    instance_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_patient(current_user)

    today = _local_today()

    inst = (
        db.query(QuestionnaireInstance)
        .filter(
            QuestionnaireInstance.id == instance_id,
            QuestionnaireInstance.patient_id == current_user.id,
        )
        .first()
    )
    if not inst:
        raise HTTPException(status_code=404, detail="Check-in instance not found")

    if inst.scheduled_for != today:
        raise HTTPException(status_code=403, detail="You can only complete a check-in on its scheduled day")

    if inst.status == CheckinStatus.COMPLETED:
        return CompleteOut(message="Already completed", instance_id=inst.id, status=inst.status)

    inst.status = CheckinStatus.COMPLETED
    inst.submitted_at = datetime.utcnow()

    _add_admin_submission_notification_safe(db, patient=current_user, instance=inst)

    db.commit()

    write_audit_log(db, "PATIENT_CHECKIN_COMPLETED", user_id=current_user.id, request=request)
    return CompleteOut(message="Completed", instance_id=inst.id, status=inst.status)


@router.get("/checkins", response_model=List[CheckinRowOut])
def list_my_checkins(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    limit: int = 100,
):
    _require_patient(current_user)

    rows = (
        db.query(QuestionnaireInstance)
        .filter(QuestionnaireInstance.patient_id == current_user.id)
        .order_by(QuestionnaireInstance.scheduled_for.desc(), QuestionnaireInstance.id.desc())
        .limit(min(max(limit, 1), 200))
        .all()
    )

    out: List[CheckinRowOut] = []
    for inst in rows:
        flow = _get_flow(db, inst.flow_id)
        total_score = _compute_instance_total_score(db, instance_id=inst.id, patient_id=current_user.id)

        out.append(
            CheckinRowOut(
                instance_id=inst.id,
                assignment_id=inst.assignment_id,
                flow_id=inst.flow_id,
                flow_name=flow.name,
                scheduled_for=inst.scheduled_for.isoformat(),
                status=inst.status,
                submitted_at=inst.submitted_at.isoformat() if inst.submitted_at else None,
                total_score=total_score,
            )
        )

    return out


@router.post("/checkins/{instance_id}/reset", response_model=dict)
def reset_checkin(
    instance_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_patient(current_user)

    inst = (
        db.query(QuestionnaireInstance)
        .filter(
            QuestionnaireInstance.id == instance_id,
            QuestionnaireInstance.patient_id == current_user.id,
        )
        .first()
    )
    if not inst:
        raise HTTPException(404, "Check-in not found")

    # 🔐 safety flag — REQUIRED
    if os.getenv("ALLOW_PATIENT_RESET") != "1":
        raise HTTPException(403, "Reset not allowed")

    db.query(QuestionnaireAnswer).filter(
        QuestionnaireAnswer.instance_id == inst.id
    ).delete()

    inst.status = CheckinStatus.IN_PROGRESS
    inst.submitted_at = None

    db.commit()

    write_audit_log(
        db,
        "PATIENT_CHECKIN_RESET",
        user_id=current_user.id,
        request=request,
        details=f"instance_id={inst.id}",
    )

    return {"message": "Check-in reset", "instance_id": inst.id}



@router.get("/attempts", response_model=AttemptsListOut)
def list_my_attempts(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    skip: int = 0,
    limit: int = 50,
):
    _require_patient(current_user)

    base = (
        db.query(QuestionnaireInstance)
        .filter(
            QuestionnaireInstance.patient_id == current_user.id,
            QuestionnaireInstance.status == CheckinStatus.COMPLETED,
        )
    )

    total = base.count()

    instances = (
        base.order_by(QuestionnaireInstance.scheduled_for.desc(), QuestionnaireInstance.id.desc())
        .offset(skip)
        .limit(min(limit, 200))
        .all()
    )

    items: List[AttemptRowOut] = []
    for inst in instances:
        flow = _get_flow(db, inst.flow_id)
        total_score = _compute_instance_total_score(db, instance_id=inst.id, patient_id=current_user.id)

        items.append(
            AttemptRowOut(
                instance_id=inst.id,
                flow_id=inst.flow_id,
                flow_name=flow.name,
                scheduled_for=inst.scheduled_for.isoformat(),
                submitted_at=inst.submitted_at.isoformat() if inst.submitted_at else None,
                total_score=total_score,
            )
        )

    return AttemptsListOut(total=total, items=items)


@router.get("/attempts/{instance_id}", response_model=AttemptDetailOut)
def get_attempt_detail(
    instance_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_patient(current_user)

    inst = (
        db.query(QuestionnaireInstance)
        .filter(
            QuestionnaireInstance.id == instance_id,
            QuestionnaireInstance.patient_id == current_user.id,
            QuestionnaireInstance.status == CheckinStatus.COMPLETED,
        )
        .first()
    )
    if not inst:
        raise HTTPException(404, "Completed attempt not found")

    flow = _get_flow(db, inst.flow_id)

    rows = (
        db.query(QuestionnaireAnswer, FlowNode, FlowNodeOption)
        .join(FlowNode, QuestionnaireAnswer.node_id == FlowNode.id)
        .outerjoin(FlowNodeOption, QuestionnaireAnswer.option_id == FlowNodeOption.id)
        .filter(
            QuestionnaireAnswer.instance_id == inst.id,
            FlowNode.node_type == FlowNodeType.QUESTION,
        )
        .order_by(FlowNode.display_order.asc())
        .all()
    )

    items: List[AttemptDetailItem] = []
    for ans, node, opt in rows:
        items.append(
            AttemptDetailItem(
                node_key=node.node_key,
                question=node.body_text,
                answer=opt.label if opt else None,
            )
        )

    return AttemptDetailOut(
        instance_id=inst.id,
        flow_name=flow.name,
        submitted_at=inst.submitted_at.isoformat() if inst.submitted_at else None,
        items=items,
    )

