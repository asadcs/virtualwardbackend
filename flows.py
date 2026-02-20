# # # from __future__ import annotations

# # # from datetime import datetime
# # # from enum import Enum
# # # from typing import Optional, List

# # # from fastapi import APIRouter, Depends, HTTPException, Request
# # # from pydantic import BaseModel, Field
# # # from sqlalchemy import (
# # #     Column,
# # #     Integer,
# # #     String,
# # #     Text,
# # #     DateTime,
# # #     ForeignKey,
# # #     Boolean,
# # #     Index,
# # #     UniqueConstraint,
# # #     Enum as SAEnum,
# # # )
# # # from sqlalchemy.orm import Session, relationship, joinedload

# # # from db import Base
# # # from auth import get_db, require_admin, write_audit_log
# # # from user import User

# # # router = APIRouter(prefix="/flows", tags=["Flows"])

# # # # ============================================================
# # # # ENUMS
# # # # ============================================================
# # # class FlowStatus(str, Enum):
# # #     DRAFT = "DRAFT"
# # #     ACTIVE = "ACTIVE"
# # #     ARCHIVED = "ARCHIVED"


# # # class FlowNodeType(str, Enum):
# # #     QUESTION = "QUESTION"
# # #     MESSAGE = "MESSAGE"
# # #     ALERT = "ALERT"


# # # class SeverityLevel(str, Enum):
# # #     GREEN = "GREEN"
# # #     AMBER = "AMBER"
# # #     RED = "RED"


# # # # ============================================================
# # # # SQLALCHEMY MODELS
# # # # ============================================================
# # # class QuestionnaireFlow(Base):
# # #     __tablename__ = "questionnaire_flows"
# # #     id = Column(Integer, primary_key=True)
# # #     name = Column(String(200), nullable=False, index=True)
# # #     description = Column(Text, nullable=True)
# # #     flow_type = Column(String(50), nullable=False, index=True)
# # #     status = Column(SAEnum(FlowStatus), nullable=False, default=FlowStatus.DRAFT, index=True)
# # #     start_node_key = Column(String(50), nullable=False)
# # #     version = Column(Integer, default=1, nullable=False)
# # #     parent_flow_id = Column(Integer, ForeignKey("questionnaire_flows.id"), nullable=True)
# # #     is_deleted = Column(Boolean, default=False, nullable=False, index=True)
# # #     created_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
# # #     created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
# # #     updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

# # #     created_by = relationship("User", foreign_keys=[created_by_user_id])
# # #     parent_flow = relationship("QuestionnaireFlow", remote_side=[id], foreign_keys=[parent_flow_id])
# # #     nodes = relationship(
# # #         "FlowNode",
# # #         back_populates="flow",
# # #         cascade="all, delete-orphan",
# # #         order_by="FlowNode.display_order",
# # #     )


# # # class FlowNode(Base):
# # #     __tablename__ = "flow_nodes"
# # #     __table_args__ = (
# # #         UniqueConstraint("flow_id", "node_key", name="uq_flow_node_key"),
# # #         Index("idx_flow_node_flow", "flow_id"),
# # #         Index("idx_flow_node_key", "node_key"),
# # #         Index("idx_flow_node_type", "node_type"),
# # #     )

# # #     id = Column(Integer, primary_key=True)
# # #     flow_id = Column(Integer, ForeignKey("questionnaire_flows.id", ondelete="CASCADE"), nullable=False)
# # #     node_key = Column(String(50), nullable=False)
# # #     node_type = Column(SAEnum(FlowNodeType), nullable=False)
# # #     title = Column(String(200), nullable=True)
# # #     body_text = Column(Text, nullable=False)
# # #     help_text = Column(Text, nullable=True)
# # #     parent_node_key = Column(String(50), nullable=True)
# # #     depth_level = Column(Integer, default=0, nullable=False)
# # #     display_order = Column(Integer, default=0, nullable=False)
# # #     default_next_node_key = Column(String(50), nullable=True)
# # #     auto_next_node_key = Column(String(50), nullable=True)
# # #     ui_ack_required = Column(Boolean, default=False, nullable=False)
# # #     alert_severity = Column(SAEnum(SeverityLevel), nullable=True)
# # #     notify_admin = Column(Boolean, default=False, nullable=False)

# # #     flow = relationship("QuestionnaireFlow", back_populates="nodes")
# # #     options = relationship(
# # #         "FlowNodeOption",
# # #         back_populates="node",
# # #         cascade="all, delete-orphan",
# # #         order_by="FlowNodeOption.display_order",
# # #     )


# # # class FlowNodeOption(Base):
# # #     __tablename__ = "flow_node_options"
# # #     id = Column(Integer, primary_key=True)
# # #     node_id = Column(Integer, ForeignKey("flow_nodes.id", ondelete="CASCADE"), nullable=False, index=True)
# # #     display_order = Column(Integer, default=0, nullable=False)
# # #     label = Column(String(200), nullable=False)
# # #     value = Column(String(200), nullable=False)
# # #     severity = Column(SAEnum(SeverityLevel), default=SeverityLevel.GREEN, nullable=False)
# # #     news2_score = Column(Integer, default=0, nullable=False)
# # #     seriousness_points = Column(Integer, default=0, nullable=False)
# # #     next_node_key = Column(String(50), nullable=True)

# # #     node = relationship("FlowNode", back_populates="options")


# # # # ============================================================
# # # # PYDANTIC SCHEMAS
# # # # ============================================================
# # # class FlowOptionIn(BaseModel):
# # #     display_order: int
# # #     label: str
# # #     value: str
# # #     severity: SeverityLevel
# # #     news2_score: int = 0
# # #     seriousness_points: int = 0
# # #     next_node_key: Optional[str] = None


# # # class FlowNodeIn(BaseModel):
# # #     node_key: str
# # #     node_type: FlowNodeType
# # #     title: Optional[str] = None
# # #     body_text: str
# # #     help_text: Optional[str] = None
# # #     parent_node_key: Optional[str] = None
# # #     default_next_node_key: Optional[str] = None
# # #     auto_next_node_key: Optional[str] = None
# # #     ui_ack_required: bool = False
# # #     alert_severity: Optional[SeverityLevel] = None
# # #     notify_admin: bool = False
# # #     options: List[FlowOptionIn] = []


# # # class FlowCreateIn(BaseModel):
# # #     name: str = Field(min_length=1, max_length=200)
# # #     description: Optional[str] = None
# # #     flow_type: str = Field(min_length=1, max_length=50)
# # #     status: FlowStatus = FlowStatus.DRAFT
# # #     start_node_key: str
# # #     nodes: List[FlowNodeIn] = Field(min_items=1)


# # # class FlowUpdateIn(BaseModel):
# # #     name: str = Field(min_length=1, max_length=200)
# # #     description: Optional[str] = None
# # #     flow_type: str = Field(min_length=1, max_length=50)
# # #     status: FlowStatus
# # #     start_node_key: str
# # #     nodes: List[FlowNodeIn] = Field(min_items=1)


# # # class FlowOptionOut(BaseModel):
# # #     id: int
# # #     display_order: int
# # #     label: str
# # #     value: str
# # #     severity: str
# # #     news2_score: int
# # #     seriousness_points: int
# # #     next_node_key: Optional[str]

# # #     class Config:
# # #         from_attributes = True


# # # class FlowNodeOut(BaseModel):
# # #     id: int
# # #     node_key: str
# # #     node_type: str
# # #     title: Optional[str]
# # #     body_text: str
# # #     help_text: Optional[str]
# # #     parent_node_key: Optional[str]
# # #     depth_level: int
# # #     default_next_node_key: Optional[str]
# # #     auto_next_node_key: Optional[str]
# # #     ui_ack_required: bool
# # #     alert_severity: Optional[str]
# # #     notify_admin: bool
# # #     options: List[FlowOptionOut]

# # #     class Config:
# # #         from_attributes = True


# # # class FlowDetailOut(BaseModel):
# # #     id: int
# # #     name: str
# # #     description: Optional[str]
# # #     flow_type: str
# # #     status: str
# # #     start_node_key: str
# # #     version: int
# # #     created_at: datetime
# # #     updated_at: datetime
# # #     created_by: dict
# # #     nodes: List[FlowNodeOut]

# # #     class Config:
# # #         from_attributes = True


# # # class FlowOut(BaseModel):
# # #     id: int
# # #     name: str
# # #     description: Optional[str]
# # #     flow_type: str
# # #     status: str
# # #     start_node_key: str
# # #     version: int
# # #     node_count: int
# # #     created_at: datetime
# # #     created_by: dict

# # #     class Config:
# # #         from_attributes = True


# # # class FlowListOut(BaseModel):
# # #     total: int
# # #     items: List[FlowOut]


# # # # ============================================================
# # # # NORMALIZE INPUT (✅ MINIMAL BUT IMPORTANT)
# # # # ============================================================
# # # def normalize_nodes_for_type(nodes: List[FlowNodeIn]) -> List[FlowNodeIn]:
# # #     """
# # #     Makes MESSAGE/ALERT safe even if frontend forgets:
# # #     - MESSAGE/ALERT must have auto_next_node_key (default END)
# # #     - MESSAGE/ALERT should not have options/default_next_node_key
# # #     - ALERT should have alert_severity (default RED)
# # #     """
# # #     normalized: List[FlowNodeIn] = []

# # #     for n in nodes:
# # #         if n.node_type in (FlowNodeType.MESSAGE, FlowNodeType.ALERT):
# # #             normalized.append(
# # #                 FlowNodeIn(
# # #                     node_key=n.node_key,
# # #                     node_type=n.node_type,
# # #                     title=n.title,
# # #                     body_text=n.body_text,
# # #                     help_text=n.help_text,
# # #                     parent_node_key=n.parent_node_key,
# # #                     default_next_node_key=None,
# # #                     auto_next_node_key=n.auto_next_node_key or "END",
# # #                     ui_ack_required=n.ui_ack_required,
# # #                     alert_severity=(n.alert_severity or SeverityLevel.RED)
# # #                     if n.node_type == FlowNodeType.ALERT
# # #                     else None,
# # #                     notify_admin=bool(n.notify_admin) if n.node_type == FlowNodeType.ALERT else False,
# # #                     options=[],  # ✅ force empty
# # #                 )
# # #             )
# # #         else:
# # #             # QUESTION: keep as-is
# # #             normalized.append(n)

# # #     return normalized


# # # # ============================================================
# # # # VALIDATION
# # # # ============================================================
# # # def validate_flow_integrity(flow: QuestionnaireFlow, nodes: List[FlowNode]) -> List[str]:
# # #     errors = []
# # #     if not nodes:
# # #         errors.append("Flow must have at least one node")
# # #         return errors

# # #     node_keys = {n.node_key for n in nodes}
# # #     if flow.start_node_key not in node_keys:
# # #         errors.append(f"start_node_key '{flow.start_node_key}' not found")

# # #     for node in nodes:
# # #         if node.node_type == FlowNodeType.QUESTION:
# # #             if not node.options or len(node.options) < 2:
# # #                 errors.append(f"Node '{node.node_key}': QUESTION must have >= 2 options")
# # #             if (
# # #                 node.default_next_node_key
# # #                 and node.default_next_node_key != "END"
# # #                 and node.default_next_node_key not in node_keys
# # #             ):
# # #                 errors.append(f"Node '{node.node_key}': invalid default_next_node_key")
# # #             for opt in node.options:
# # #                 if opt.next_node_key and opt.next_node_key != "END" and opt.next_node_key not in node_keys:
# # #                     errors.append(f"Node '{node.node_key}', option '{opt.label}': invalid next_node_key")

# # #         elif node.node_type in (FlowNodeType.MESSAGE, FlowNodeType.ALERT):
# # #             if not node.auto_next_node_key:
# # #                 errors.append(f"Node '{node.node_key}': {node.node_type.value} must have auto_next_node_key")
# # #             elif node.auto_next_node_key != "END" and node.auto_next_node_key not in node_keys:
# # #                 errors.append(f"Node '{node.node_key}': invalid auto_next_node_key")

# # #             # ✅ extra safety: message/alert should not have options
# # #             if node.options and len(node.options) > 0:
# # #                 errors.append(f"Node '{node.node_key}': {node.node_type.value} must not have options")

# # #             # ✅ alert should have severity
# # #             if node.node_type == FlowNodeType.ALERT and not node.alert_severity:
# # #                 errors.append(f"Node '{node.node_key}': ALERT must have alert_severity")

# # #     def has_cycle(current: str, visited: set, stack: set) -> bool:
# # #         if current == "END" or current in visited:
# # #             return current in stack
# # #         visited.add(current)
# # #         stack.add(current)

# # #         node = next((n for n in nodes if n.node_key == current), None)
# # #         if node:
# # #             next_keys = []
# # #             if node.node_type == FlowNodeType.QUESTION:
# # #                 if node.default_next_node_key:
# # #                     next_keys.append(node.default_next_node_key)
# # #                 for opt in node.options:
# # #                     if opt.next_node_key:
# # #                         next_keys.append(opt.next_node_key)
# # #             else:
# # #                 if node.auto_next_node_key:
# # #                     next_keys.append(node.auto_next_node_key)

# # #             for nk in next_keys:
# # #                 if has_cycle(nk, visited, stack):
# # #                     return True

# # #         stack.remove(current)
# # #         return False

# # #     if has_cycle(flow.start_node_key, set(), set()):
# # #         errors.append("Flow contains cycles")

# # #     return errors


# # # # ============================================================
# # # # HELPER (options attach via relationship ✅)
# # # # ============================================================
# # # def _create_nodes_from_data(flow_id: int, nodes_data: List[FlowNodeIn], db: Session) -> List[FlowNode]:
# # #     created_nodes: List[FlowNode] = []

# # #     for idx, node_data in enumerate(nodes_data):
# # #         node = FlowNode(
# # #             flow_id=flow_id,
# # #             node_key=node_data.node_key,
# # #             node_type=node_data.node_type,
# # #             title=node_data.title,
# # #             body_text=node_data.body_text,
# # #             help_text=node_data.help_text,
# # #             parent_node_key=node_data.parent_node_key,
# # #             depth_level=node_data.node_key.count("."),
# # #             display_order=idx,
# # #             default_next_node_key=node_data.default_next_node_key,
# # #             auto_next_node_key=node_data.auto_next_node_key,
# # #             ui_ack_required=node_data.ui_ack_required,
# # #             alert_severity=node_data.alert_severity,
# # #             notify_admin=node_data.notify_admin,
# # #         )

# # #         for opt_data in (node_data.options or []):
# # #             node.options.append(
# # #                 FlowNodeOption(
# # #                     display_order=opt_data.display_order,
# # #                     label=opt_data.label,
# # #                     value=opt_data.value,
# # #                     severity=opt_data.severity,
# # #                     news2_score=opt_data.news2_score,
# # #                     seriousness_points=opt_data.seriousness_points,
# # #                     next_node_key=opt_data.next_node_key,
# # #                 )
# # #             )

# # #         db.add(node)
# # #         created_nodes.append(node)

# # #     db.flush()
# # #     return created_nodes


# # # # ============================================================
# # # # ROUTES - CREATE
# # # # ============================================================
# # # @router.post("/", response_model=dict)
# # # def create_flow(
# # #     data: FlowCreateIn,
# # #     request: Request,
# # #     db: Session = Depends(get_db),
# # #     current_user: User = Depends(require_admin),
# # # ):
# # #     # ✅ normalize nodes before creating
# # #     normalized_nodes = normalize_nodes_for_type(data.nodes)

# # #     flow = QuestionnaireFlow(
# # #         name=data.name,
# # #         description=data.description,
# # #         flow_type=data.flow_type,
# # #         status=data.status,
# # #         start_node_key=data.start_node_key,
# # #         version=1,
# # #         created_by_user_id=current_user.id,
# # #     )
# # #     db.add(flow)
# # #     db.flush()

# # #     created_nodes = _create_nodes_from_data(flow.id, normalized_nodes, db)
# # #     errors = validate_flow_integrity(flow, created_nodes)
# # #     if errors:
# # #         db.rollback()
# # #         raise HTTPException(400, detail={"errors": errors})

# # #     db.commit()
# # #     db.refresh(flow)

# # #     write_audit_log(db, "FLOW_CREATED", user_id=current_user.id, request=request, details=f"flow_id={flow.id}")
# # #     return {"flow_id": flow.id, "message": "Flow created successfully"}


# # # # ============================================================
# # # # ROUTES - READ
# # # # ============================================================
# # # @router.get("/", response_model=FlowListOut)
# # # def list_flows(
# # #     db: Session = Depends(get_db),
# # #     current_user: User = Depends(require_admin),
# # #     q: Optional[str] = None,
# # #     flow_type: Optional[str] = None,
# # #     status: Optional[FlowStatus] = None,
# # #     skip: int = 0,
# # #     limit: int = 20,
# # # ):
# # #     query = (
# # #         db.query(QuestionnaireFlow)
# # #         .options(joinedload(QuestionnaireFlow.created_by))
# # #         .filter(QuestionnaireFlow.is_deleted == False)  # noqa: E712
# # #     )

# # #     if q:
# # #         query = query.filter(QuestionnaireFlow.name.ilike(f"%{q.strip()}%"))
# # #     if flow_type:
# # #         query = query.filter(QuestionnaireFlow.flow_type == flow_type)
# # #     if status:
# # #         query = query.filter(QuestionnaireFlow.status == status)

# # #     total = query.count()
# # #     flows = (
# # #         query.order_by(QuestionnaireFlow.created_at.desc())
# # #         .offset(skip)
# # #         .limit(min(limit, 100))
# # #         .all()
# # #     )

# # #     items = [
# # #         FlowOut(
# # #             id=f.id,
# # #             name=f.name,
# # #             description=f.description,
# # #             flow_type=f.flow_type,
# # #             status=f.status.value,
# # #             start_node_key=f.start_node_key,
# # #             version=f.version,
# # #             node_count=db.query(FlowNode).filter(FlowNode.flow_id == f.id).count(),
# # #             created_at=f.created_at,
# # #             created_by={
# # #                 "id": f.created_by.id,
# # #                 "name": f.created_by.name,
# # #                 "email": f.created_by.email,
# # #             },
# # #         )
# # #         for f in flows
# # #     ]

# # #     return FlowListOut(total=total, items=items)


# # # @router.get("/{flow_id}", response_model=FlowDetailOut)
# # # def get_flow(
# # #     flow_id: int,
# # #     db: Session = Depends(get_db),
# # #     current_user: User = Depends(require_admin),
# # # ):
# # #     flow = (
# # #         db.query(QuestionnaireFlow)
# # #         .options(
# # #             joinedload(QuestionnaireFlow.created_by),
# # #             joinedload(QuestionnaireFlow.nodes).joinedload(FlowNode.options),
# # #         )
# # #         .filter(
# # #             QuestionnaireFlow.id == flow_id,
# # #             QuestionnaireFlow.is_deleted == False,  # noqa: E712
# # #         )
# # #         .first()
# # #     )

# # #     if not flow:
# # #         raise HTTPException(404, "Flow not found")

# # #     return FlowDetailOut(
# # #         id=flow.id,
# # #         name=flow.name,
# # #         description=flow.description,
# # #         flow_type=flow.flow_type,
# # #         status=flow.status.value,
# # #         start_node_key=flow.start_node_key,
# # #         version=flow.version,
# # #         created_at=flow.created_at,
# # #         updated_at=flow.updated_at,
# # #         created_by={
# # #             "id": flow.created_by.id,
# # #             "name": flow.created_by.name,
# # #             "email": flow.created_by.email,
# # #         },
# # #         nodes=[
# # #             FlowNodeOut(
# # #                 id=n.id,
# # #                 node_key=n.node_key,
# # #                 node_type=n.node_type.value,
# # #                 title=n.title,
# # #                 body_text=n.body_text,
# # #                 help_text=n.help_text,
# # #                 parent_node_key=n.parent_node_key,
# # #                 depth_level=n.depth_level,
# # #                 default_next_node_key=n.default_next_node_key,
# # #                 auto_next_node_key=n.auto_next_node_key,
# # #                 ui_ack_required=n.ui_ack_required,
# # #                 alert_severity=n.alert_severity.value if n.alert_severity else None,
# # #                 notify_admin=n.notify_admin,
# # #                 options=[
# # #                     FlowOptionOut(
# # #                         id=o.id,
# # #                         display_order=o.display_order,
# # #                         label=o.label,
# # #                         value=o.value,
# # #                         severity=o.severity.value,
# # #                         news2_score=o.news2_score,
# # #                         seriousness_points=o.seriousness_points,
# # #                         next_node_key=o.next_node_key,
# # #                     )
# # #                     for o in n.options
# # #                 ],
# # #             )
# # #             for n in flow.nodes
# # #         ],
# # #     )


# # # # ============================================================
# # # # ROUTES - UPDATE
# # # # ============================================================
# # # @router.put("/{flow_id}", response_model=dict)
# # # def update_flow(
# # #     flow_id: int,
# # #     data: FlowUpdateIn,
# # #     request: Request,
# # #     db: Session = Depends(get_db),
# # #     current_user: User = Depends(require_admin),
# # # ):
# # #     flow = (
# # #         db.query(QuestionnaireFlow)
# # #         .filter(
# # #             QuestionnaireFlow.id == flow_id,
# # #             QuestionnaireFlow.is_deleted == False,  # noqa: E712
# # #         )
# # #         .first()
# # #     )

# # #     if not flow:
# # #         raise HTTPException(404, "Flow not found")

# # #     # ✅ normalize nodes before saving
# # #     normalized_nodes = normalize_nodes_for_type(data.nodes)

# # #     # Delete old nodes
# # #     db.query(FlowNode).filter(FlowNode.flow_id == flow.id).delete()

# # #     # Update flow
# # #     flow.name = data.name
# # #     flow.description = data.description
# # #     flow.flow_type = data.flow_type
# # #     flow.status = data.status
# # #     flow.start_node_key = data.start_node_key
# # #     flow.version += 1
# # #     flow.updated_at = datetime.utcnow()

# # #     db.flush()

# # #     # Create new nodes
# # #     created_nodes = _create_nodes_from_data(flow.id, normalized_nodes, db)
# # #     errors = validate_flow_integrity(flow, created_nodes)
# # #     if errors:
# # #         db.rollback()
# # #         raise HTTPException(400, detail={"errors": errors})

# # #     db.commit()
# # #     db.refresh(flow)

# # #     write_audit_log(
# # #         db,
# # #         "FLOW_UPDATED",
# # #         user_id=current_user.id,
# # #         request=request,
# # #         details=f"flow_id={flow.id}, version={flow.version}",
# # #     )
# # #     return {"flow_id": flow.id, "version": flow.version, "message": "Flow updated successfully"}


# # # # ============================================================
# # # # ROUTES - DELETE
# # # # ============================================================
# # # @router.delete("/{flow_id}", response_model=dict)
# # # def delete_flow(
# # #     flow_id: int,
# # #     request: Request,
# # #     db: Session = Depends(get_db),
# # #     current_user: User = Depends(require_admin),
# # # ):
# # #     flow = (
# # #         db.query(QuestionnaireFlow)
# # #         .filter(
# # #             QuestionnaireFlow.id == flow_id,
# # #             QuestionnaireFlow.is_deleted == False,  # noqa: E712
# # #         )
# # #         .first()
# # #     )

# # #     if not flow:
# # #         raise HTTPException(404, "Flow not found")

# # #     flow.is_deleted = True
# # #     db.commit()

# # #     write_audit_log(db, "FLOW_DELETED", user_id=current_user.id, request=request, details=f"flow_id={flow.id}")
# # #     return {"message": "Flow deleted successfully"}


# # # # ============================================================
# # # # ROUTES - DEMO SEED
# # # # ============================================================
# # # @router.post("/demo/seed", response_model=dict)
# # # def create_demo_flow(
# # #     request: Request,
# # #     db: Session = Depends(get_db),
# # #     current_user: User = Depends(require_admin),
# # # ):
# # #     demo_data = FlowCreateIn(
# # #         name="Virtual Ward Daily Check-in Demo",
# # #         description="Daily health monitoring questionnaire with conditional paths",
# # #         flow_type="DAILY_CHECKIN",
# # #         status=FlowStatus.ACTIVE,
# # #         start_node_key="1",
# # #         nodes=[
# # #             FlowNodeIn(
# # #                 node_key="1",
# # #                 node_type=FlowNodeType.QUESTION,
# # #                 title="Temperature Check",
# # #                 body_text="What is your temperature today?",
# # #                 help_text="Use a thermometer and record in Celsius",
# # #                 parent_node_key=None,
# # #                 default_next_node_key="2",
# # #                 options=[
# # #                     FlowOptionIn(display_order=1, label="< 37.8°C (Normal)", value="normal", severity=SeverityLevel.GREEN, news2_score=0, seriousness_points=0, next_node_key="2"),
# # #                     FlowOptionIn(display_order=2, label="37.8-39°C (Mild)", value="mild", severity=SeverityLevel.AMBER, news2_score=1, seriousness_points=1, next_node_key="1.1"),
# # #                     FlowOptionIn(display_order=3, label="> 39°C (High)", value="high", severity=SeverityLevel.RED, news2_score=2, seriousness_points=3, next_node_key="1.2"),
# # #                 ],
# # #             ),
# # #             FlowNodeIn(
# # #                 node_key="1.1",
# # #                 node_type=FlowNodeType.ALERT,
# # #                 title="Mild Fever Alert",
# # #                 body_text="You have a mild fever. Monitor your temperature and stay hydrated.",
# # #                 auto_next_node_key="2",
# # #                 alert_severity=SeverityLevel.AMBER,
# # #                 notify_admin=False,
# # #                 options=[],
# # #             ),
# # #             FlowNodeIn(
# # #                 node_key="1.2",
# # #                 node_type=FlowNodeType.ALERT,
# # #                 title="High Fever Alert",
# # #                 body_text="⚠️ High fever detected. Please contact your healthcare provider immediately.",
# # #                 auto_next_node_key="END",
# # #                 alert_severity=SeverityLevel.RED,
# # #                 notify_admin=True,
# # #                 options=[],
# # #             ),
# # #             FlowNodeIn(
# # #                 node_key="2",
# # #                 node_type=FlowNodeType.QUESTION,
# # #                 title="Breathing Check",
# # #                 body_text="How is your breathing today?",
# # #                 help_text="Rate your breathing difficulty",
# # #                 parent_node_key="1",
# # #                 default_next_node_key="END",
# # #                 options=[
# # #                     FlowOptionIn(display_order=1, label="Normal", value="normal", severity=SeverityLevel.GREEN, news2_score=0, seriousness_points=0, next_node_key="END"),
# # #                     FlowOptionIn(display_order=2, label="Slightly difficult", value="mild", severity=SeverityLevel.AMBER, news2_score=1, seriousness_points=1, next_node_key="END"),
# # #                     FlowOptionIn(display_order=3, label="Very difficult", value="severe", severity=SeverityLevel.RED, news2_score=3, seriousness_points=3, next_node_key="2.1"),
# # #                 ],
# # #             ),
# # #             FlowNodeIn(
# # #                 node_key="2.1",
# # #                 node_type=FlowNodeType.ALERT,
# # #                 title="Breathing Difficulty Alert",
# # #                 body_text="⚠️ Severe breathing difficulty detected. Seek immediate medical attention!",
# # #                 auto_next_node_key="END",
# # #                 alert_severity=SeverityLevel.RED,
# # #                 notify_admin=True,
# # #                 options=[],
# # #             ),
# # #         ],
# # #     )

# # #     # ✅ normalize (keeps demo safe too)
# # #     normalized_nodes = normalize_nodes_for_type(demo_data.nodes)

# # #     flow = QuestionnaireFlow(
# # #         name=demo_data.name,
# # #         description=demo_data.description,
# # #         flow_type=demo_data.flow_type,
# # #         status=demo_data.status,
# # #         start_node_key=demo_data.start_node_key,
# # #         version=1,
# # #         created_by_user_id=current_user.id,
# # #     )
# # #     db.add(flow)
# # #     db.flush()

# # #     created_nodes = _create_nodes_from_data(flow.id, normalized_nodes, db)
# # #     errors = validate_flow_integrity(flow, created_nodes)
# # #     if errors:
# # #         db.rollback()
# # #         raise HTTPException(400, detail={"errors": errors})

# # #     db.commit()
# # #     db.refresh(flow)

# # #     write_audit_log(db, "DEMO_FLOW_CREATED", user_id=current_user.id, request=request, details=f"flow_id={flow.id}")
# # #     return {"flow_id": flow.id, "message": "Demo flow created successfully"}


# # # # ============================================================
# # # # ROUTES - VALIDATE
# # # # ============================================================
# # # @router.get("/{flow_id}/validate", response_model=dict)
# # # def validate_flow(
# # #     flow_id: int,
# # #     db: Session = Depends(get_db),
# # #     current_user: User = Depends(require_admin),
# # # ):
# # #     flow = (
# # #         db.query(QuestionnaireFlow)
# # #         .options(joinedload(QuestionnaireFlow.nodes).joinedload(FlowNode.options))
# # #         .filter(
# # #             QuestionnaireFlow.id == flow_id,
# # #             QuestionnaireFlow.is_deleted == False,  # noqa: E712
# # #         )
# # #         .first()
# # #     )

# # #     if not flow:
# # #         raise HTTPException(404, "Flow not found")

# # #     errors = validate_flow_integrity(flow, flow.nodes)
# # #     return {"flow_id": flow.id, "valid": len(errors) == 0, "errors": errors}

# # # flows.py
# # from __future__ import annotations

# # from datetime import datetime
# # from enum import Enum
# # from typing import Optional, List, Dict, Set

# # from fastapi import APIRouter, Depends, HTTPException, Request
# # from pydantic import BaseModel, Field
# # from sqlalchemy import (
# #     Column,
# #     Integer,
# #     String,
# #     Text,
# #     DateTime,
# #     ForeignKey,
# #     Boolean,
# #     Index,
# #     UniqueConstraint,
# #     Enum as SAEnum,
# # )
# # from sqlalchemy.orm import Session, relationship, joinedload

# # from db import Base
# # from auth import get_db, require_admin, write_audit_log
# # from user import User

# # router = APIRouter(prefix="/flows", tags=["Flows"])


# # # ============================================================
# # # ENUMS
# # # ============================================================
# # class FlowStatus(str, Enum):
# #     DRAFT = "DRAFT"
# #     ACTIVE = "ACTIVE"
# #     ARCHIVED = "ARCHIVED"


# # class FlowNodeType(str, Enum):
# #     QUESTION = "QUESTION"
# #     MESSAGE = "MESSAGE"
# #     ALERT = "ALERT"


# # class SeverityLevel(str, Enum):
# #     GREEN = "GREEN"
# #     AMBER = "AMBER"
# #     RED = "RED"


# # # ============================================================
# # # SQLALCHEMY MODELS
# # # ============================================================
# # class QuestionnaireFlow(Base):
# #     __tablename__ = "questionnaire_flows"

# #     id = Column(Integer, primary_key=True)
# #     name = Column(String(200), nullable=False, index=True)
# #     description = Column(Text, nullable=True)
# #     flow_type = Column(String(50), nullable=False, index=True)
# #     status = Column(SAEnum(FlowStatus), nullable=False, default=FlowStatus.DRAFT, index=True)

# #     start_node_key = Column(String(50), nullable=False)

# #     version = Column(Integer, default=1, nullable=False)
# #     parent_flow_id = Column(Integer, ForeignKey("questionnaire_flows.id"), nullable=True)

# #     is_deleted = Column(Boolean, default=False, nullable=False, index=True)

# #     created_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
# #     created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
# #     updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

# #     created_by = relationship("User", foreign_keys=[created_by_user_id])
# #     parent_flow = relationship("QuestionnaireFlow", remote_side=[id], foreign_keys=[parent_flow_id])

# #     nodes = relationship(
# #         "FlowNode",
# #         back_populates="flow",
# #         cascade="all, delete-orphan",
# #         order_by="FlowNode.display_order",
# #     )


# # class FlowNode(Base):
# #     __tablename__ = "flow_nodes"
# #     __table_args__ = (
# #         UniqueConstraint("flow_id", "node_key", name="uq_flow_node_key"),
# #         Index("idx_flow_node_flow", "flow_id"),
# #         Index("idx_flow_node_key", "node_key"),
# #         Index("idx_flow_node_type", "node_type"),
# #     )

# #     id = Column(Integer, primary_key=True)
# #     flow_id = Column(Integer, ForeignKey("questionnaire_flows.id", ondelete="CASCADE"), nullable=False)

# #     node_key = Column(String(50), nullable=False)
# #     node_type = Column(SAEnum(FlowNodeType), nullable=False)

# #     title = Column(String(200), nullable=True)
# #     body_text = Column(Text, nullable=False)
# #     help_text = Column(Text, nullable=True)

# #     parent_node_key = Column(String(50), nullable=True)

# #     depth_level = Column(Integer, default=0, nullable=False)
# #     display_order = Column(Integer, default=0, nullable=False)

# #     default_next_node_key = Column(String(50), nullable=True)
# #     auto_next_node_key = Column(String(50), nullable=True)

# #     ui_ack_required = Column(Boolean, default=False, nullable=False)

# #     alert_severity = Column(SAEnum(SeverityLevel), nullable=True)
# #     notify_admin = Column(Boolean, default=False, nullable=False)

# #     flow = relationship("QuestionnaireFlow", back_populates="nodes")
# #     options = relationship(
# #         "FlowNodeOption",
# #         back_populates="node",
# #         cascade="all, delete-orphan",
# #         order_by="FlowNodeOption.display_order",
# #     )


# # class FlowNodeOption(Base):
# #     __tablename__ = "flow_node_options"

# #     id = Column(Integer, primary_key=True)
# #     node_id = Column(Integer, ForeignKey("flow_nodes.id", ondelete="CASCADE"), nullable=False, index=True)

# #     display_order = Column(Integer, default=0, nullable=False)
# #     label = Column(String(200), nullable=False)
# #     value = Column(String(200), nullable=False)

# #     severity = Column(SAEnum(SeverityLevel), default=SeverityLevel.GREEN, nullable=False)
# #     news2_score = Column(Integer, default=0, nullable=False)
# #     seriousness_points = Column(Integer, default=0, nullable=False)

# #     next_node_key = Column(String(50), nullable=True)

# #     node = relationship("FlowNode", back_populates="options")


# # # ============================================================
# # # PYDANTIC SCHEMAS
# # # ============================================================
# # class FlowOptionIn(BaseModel):
# #     display_order: int
# #     label: str
# #     value: str
# #     severity: SeverityLevel
# #     news2_score: int = 0
# #     seriousness_points: int = 0
# #     next_node_key: Optional[str] = None


# # class FlowNodeIn(BaseModel):
# #     node_key: str
# #     node_type: FlowNodeType
# #     title: Optional[str] = None
# #     body_text: str
# #     help_text: Optional[str] = None
# #     parent_node_key: Optional[str] = None
# #     default_next_node_key: Optional[str] = None
# #     auto_next_node_key: Optional[str] = None
# #     ui_ack_required: bool = False
# #     alert_severity: Optional[SeverityLevel] = None
# #     notify_admin: bool = False
# #     options: List[FlowOptionIn] = Field(default_factory=list)


# # class FlowCreateIn(BaseModel):
# #     name: str = Field(min_length=1, max_length=200)
# #     description: Optional[str] = None
# #     flow_type: str = Field(min_length=1, max_length=50)
# #     status: FlowStatus = FlowStatus.DRAFT
# #     start_node_key: str
# #     nodes: List[FlowNodeIn] = Field(min_items=1)


# # class FlowUpdateIn(BaseModel):
# #     name: str = Field(min_length=1, max_length=200)
# #     description: Optional[str] = None
# #     flow_type: str = Field(min_length=1, max_length=50)
# #     status: FlowStatus
# #     start_node_key: str
# #     nodes: List[FlowNodeIn] = Field(min_items=1)


# # class FlowOptionOut(BaseModel):
# #     id: int
# #     display_order: int
# #     label: str
# #     value: str
# #     severity: str
# #     news2_score: int
# #     seriousness_points: int
# #     next_node_key: Optional[str]

# #     class Config:
# #         from_attributes = True


# # class FlowNodeOut(BaseModel):
# #     id: int
# #     node_key: str
# #     node_type: str
# #     title: Optional[str]
# #     body_text: str
# #     help_text: Optional[str]
# #     parent_node_key: Optional[str]
# #     depth_level: int
# #     default_next_node_key: Optional[str]
# #     auto_next_node_key: Optional[str]
# #     ui_ack_required: bool
# #     alert_severity: Optional[str]
# #     notify_admin: bool
# #     options: List[FlowOptionOut]

# #     class Config:
# #         from_attributes = True


# # class FlowDetailOut(BaseModel):
# #     id: int
# #     name: str
# #     description: Optional[str]
# #     flow_type: str
# #     status: str
# #     start_node_key: str
# #     version: int
# #     created_at: datetime
# #     updated_at: datetime
# #     created_by: dict
# #     nodes: List[FlowNodeOut]

# #     class Config:
# #         from_attributes = True


# # class FlowOut(BaseModel):
# #     id: int
# #     name: str
# #     description: Optional[str]
# #     flow_type: str
# #     status: str
# #     start_node_key: str
# #     version: int
# #     node_count: int
# #     created_at: datetime
# #     created_by: dict

# #     class Config:
# #         from_attributes = True


# # class FlowListOut(BaseModel):
# #     total: int
# #     items: List[FlowOut]


# # # ============================================================
# # # NORMALIZE INPUT
# # # ============================================================
# # def normalize_nodes_for_type(nodes: List[FlowNodeIn]) -> List[FlowNodeIn]:
# #     """
# #     MESSAGE/ALERT safe defaults:
# #     - force options=[]
# #     - clear default_next_node_key
# #     - ensure auto_next_node_key (default END)
# #     - ALERT default severity RED
# #     """
# #     normalized: List[FlowNodeIn] = []

# #     for n in nodes:
# #         if n.node_type in (FlowNodeType.MESSAGE, FlowNodeType.ALERT):
# #             normalized.append(
# #                 FlowNodeIn(
# #                     node_key=n.node_key,
# #                     node_type=n.node_type,
# #                     title=n.title,
# #                     body_text=n.body_text,
# #                     help_text=n.help_text,
# #                     parent_node_key=n.parent_node_key,
# #                     default_next_node_key=None,
# #                     auto_next_node_key=n.auto_next_node_key or "END",
# #                     ui_ack_required=n.ui_ack_required,
# #                     alert_severity=(n.alert_severity or SeverityLevel.RED) if n.node_type == FlowNodeType.ALERT else None,
# #                     notify_admin=bool(n.notify_admin) if n.node_type == FlowNodeType.ALERT else False,
# #                     options=[],
# #                 )
# #             )
# #         else:
# #             normalized.append(n)

# #     return normalized


# # # ============================================================
# # # VALIDATION
# # # ============================================================
# # def validate_flow_integrity(flow: QuestionnaireFlow, nodes: List[FlowNode]) -> List[str]:
# #     errors: List[str] = []
# #     if not nodes:
# #         return ["Flow must have at least one node"]

# #     node_keys = {n.node_key for n in nodes}
# #     if flow.start_node_key not in node_keys:
# #         errors.append(f"start_node_key '{flow.start_node_key}' not found")

# #     for node in nodes:
# #         if node.node_type == FlowNodeType.QUESTION:
# #             if not node.options or len(node.options) < 2:
# #                 errors.append(f"Node '{node.node_key}': QUESTION must have >= 2 options")

# #             if node.default_next_node_key and node.default_next_node_key != "END" and node.default_next_node_key not in node_keys:
# #                 errors.append(f"Node '{node.node_key}': invalid default_next_node_key")

# #             for opt in node.options:
# #                 if opt.next_node_key and opt.next_node_key != "END" and opt.next_node_key not in node_keys:
# #                     errors.append(f"Node '{node.node_key}', option '{opt.label}': invalid next_node_key")

# #         elif node.node_type in (FlowNodeType.MESSAGE, FlowNodeType.ALERT):
# #             if not node.auto_next_node_key:
# #                 errors.append(f"Node '{node.node_key}': {node.node_type.value} must have auto_next_node_key")
# #             elif node.auto_next_node_key != "END" and node.auto_next_node_key not in node_keys:
# #                 errors.append(f"Node '{node.node_key}': invalid auto_next_node_key")

# #             if node.options and len(node.options) > 0:
# #                 errors.append(f"Node '{node.node_key}': {node.node_type.value} must not have options")

# #             if node.node_type == FlowNodeType.ALERT and not node.alert_severity:
# #                 errors.append(f"Node '{node.node_key}': ALERT must have alert_severity")

# #     # Standard DFS cycle detection
# #     graph: Dict[str, List[str]] = {}

# #     def add_edge(src: str, dst: Optional[str]):
# #         if not dst:
# #             return
# #         graph.setdefault(src, [])
# #         graph[src].append(dst)

# #     for n in nodes:
# #         if n.node_type == FlowNodeType.QUESTION:
# #             add_edge(n.node_key, n.default_next_node_key)
# #             for o in n.options:
# #                 add_edge(n.node_key, o.next_node_key)
# #         else:
# #             add_edge(n.node_key, n.auto_next_node_key)

# #     visited: Set[str] = set()
# #     stack: Set[str] = set()

# #     def dfs(u: str) -> bool:
# #         if u == "END":
# #             return False
# #         if u in stack:
# #             return True
# #         if u in visited:
# #             return False
# #         visited.add(u)
# #         stack.add(u)
# #         for v in graph.get(u, []):
# #             if dfs(v):
# #                 return True
# #         stack.remove(u)
# #         return False

# #     if flow.start_node_key in node_keys and dfs(flow.start_node_key):
# #         errors.append("Flow contains cycles")

# #     return errors


# # # ============================================================
# # # HELPER
# # # ============================================================
# # def _create_nodes_from_data(flow_id: int, nodes_data: List[FlowNodeIn], db: Session) -> List[FlowNode]:
# #     created_nodes: List[FlowNode] = []

# #     for idx, node_data in enumerate(nodes_data):
# #         node = FlowNode(
# #             flow_id=flow_id,
# #             node_key=node_data.node_key,
# #             node_type=node_data.node_type,
# #             title=node_data.title,
# #             body_text=node_data.body_text,
# #             help_text=node_data.help_text,
# #             parent_node_key=node_data.parent_node_key,
# #             depth_level=node_data.node_key.count("."),
# #             display_order=idx,
# #             default_next_node_key=node_data.default_next_node_key,
# #             auto_next_node_key=node_data.auto_next_node_key,
# #             ui_ack_required=node_data.ui_ack_required,
# #             alert_severity=node_data.alert_severity,
# #             notify_admin=node_data.notify_admin,
# #         )

# #         for opt_data in (node_data.options or []):
# #             node.options.append(
# #                 FlowNodeOption(
# #                     display_order=opt_data.display_order,
# #                     label=opt_data.label,
# #                     value=opt_data.value,
# #                     severity=opt_data.severity,
# #                     news2_score=opt_data.news2_score,
# #                     seriousness_points=opt_data.seriousness_points,
# #                     next_node_key=opt_data.next_node_key,
# #                 )
# #             )

# #         db.add(node)
# #         created_nodes.append(node)

# #     db.flush()
# #     return created_nodes


# # def _safe_user_name(u: Optional[User]) -> str:
# #     if not u:
# #         return ""
# #     return (getattr(u, "name", None) or getattr(u, "full_name", None) or "").strip()


# # # ============================================================
# # # ROUTES - CREATE
# # # ============================================================
# # @router.post("/", response_model=dict)
# # def create_flow(
# #     data: FlowCreateIn,
# #     request: Request,
# #     db: Session = Depends(get_db),
# #     current_user: User = Depends(require_admin),
# # ):
# #     normalized_nodes = normalize_nodes_for_type(data.nodes)

# #     flow = QuestionnaireFlow(
# #         name=data.name,
# #         description=data.description,
# #         flow_type=data.flow_type,
# #         status=data.status,
# #         start_node_key=data.start_node_key,
# #         version=1,
# #         created_by_user_id=current_user.id,
# #     )
# #     db.add(flow)
# #     db.flush()

# #     created_nodes = _create_nodes_from_data(flow.id, normalized_nodes, db)
# #     errors = validate_flow_integrity(flow, created_nodes)
# #     if errors:
# #         db.rollback()
# #         raise HTTPException(400, detail={"errors": errors})

# #     db.commit()
# #     db.refresh(flow)

# #     write_audit_log(db, "FLOW_CREATED", user_id=current_user.id, request=request, details=f"flow_id={flow.id}")
# #     return {"flow_id": flow.id, "message": "Flow created successfully"}


# # # ============================================================
# # # ROUTES - LIST
# # # ============================================================
# # @router.get("/", response_model=FlowListOut)
# # def list_flows(
# #     db: Session = Depends(get_db),
# #     current_user: User = Depends(require_admin),
# #     q: Optional[str] = None,
# #     flow_type: Optional[str] = None,
# #     status: Optional[FlowStatus] = None,
# #     skip: int = 0,
# #     limit: int = 20,
# # ):
# #     query = (
# #         db.query(QuestionnaireFlow)
# #         .options(joinedload(QuestionnaireFlow.created_by))
# #         .filter(QuestionnaireFlow.is_deleted == False)  # noqa: E712
# #     )

# #     if q:
# #         query = query.filter(QuestionnaireFlow.name.ilike(f"%{q.strip()}%"))
# #     if flow_type:
# #         query = query.filter(QuestionnaireFlow.flow_type == flow_type)
# #     if status:
# #         query = query.filter(QuestionnaireFlow.status == status)

# #     total = query.count()
# #     flows = (
# #         query.order_by(QuestionnaireFlow.created_at.desc())
# #         .offset(skip)
# #         .limit(min(limit, 100))
# #         .all()
# #     )

# #     items: List[FlowOut] = []
# #     for f in flows:
# #         items.append(
# #             FlowOut(
# #                 id=f.id,
# #                 name=f.name,
# #                 description=f.description,
# #                 flow_type=f.flow_type,
# #                 status=f.status.value,
# #                 start_node_key=f.start_node_key,
# #                 version=f.version,
# #                 node_count=db.query(FlowNode).filter(FlowNode.flow_id == f.id).count(),
# #                 created_at=f.created_at,
# #                 created_by={
# #                     "id": f.created_by.id if f.created_by else None,
# #                     "name": _safe_user_name(f.created_by),
# #                     "email": getattr(f.created_by, "email", "") if f.created_by else "",
# #                 },
# #             )
# #         )

# #     return FlowListOut(total=total, items=items)


# # # ============================================================
# # # ROUTES - GET DETAIL
# # # ============================================================
# # @router.get("/{flow_id}", response_model=FlowDetailOut)
# # def get_flow(
# #     flow_id: int,
# #     db: Session = Depends(get_db),
# #     current_user: User = Depends(require_admin),
# # ):
# #     flow = (
# #         db.query(QuestionnaireFlow)
# #         .options(
# #             joinedload(QuestionnaireFlow.created_by),
# #             joinedload(QuestionnaireFlow.nodes).joinedload(FlowNode.options),
# #         )
# #         .filter(
# #             QuestionnaireFlow.id == flow_id,
# #             QuestionnaireFlow.is_deleted == False,  # noqa: E712
# #         )
# #         .first()
# #     )

# #     if not flow:
# #         raise HTTPException(404, "Flow not found")

# #     return FlowDetailOut(
# #         id=flow.id,
# #         name=flow.name,
# #         description=flow.description,
# #         flow_type=flow.flow_type,
# #         status=flow.status.value,
# #         start_node_key=flow.start_node_key,
# #         version=flow.version,
# #         created_at=flow.created_at,
# #         updated_at=flow.updated_at,
# #         created_by={
# #             "id": flow.created_by.id if flow.created_by else None,
# #             "name": _safe_user_name(flow.created_by),
# #             "email": getattr(flow.created_by, "email", "") if flow.created_by else "",
# #         },
# #         nodes=[
# #             FlowNodeOut(
# #                 id=n.id,
# #                 node_key=n.node_key,
# #                 node_type=n.node_type.value,
# #                 title=n.title,
# #                 body_text=n.body_text,
# #                 help_text=n.help_text,
# #                 parent_node_key=n.parent_node_key,
# #                 depth_level=n.depth_level,
# #                 default_next_node_key=n.default_next_node_key,
# #                 auto_next_node_key=n.auto_next_node_key,
# #                 ui_ack_required=n.ui_ack_required,
# #                 alert_severity=n.alert_severity.value if n.alert_severity else None,
# #                 notify_admin=n.notify_admin,
# #                 options=[
# #                     FlowOptionOut(
# #                         id=o.id,
# #                         display_order=o.display_order,
# #                         label=o.label,
# #                         value=o.value,
# #                         severity=o.severity.value,
# #                         news2_score=o.news2_score,
# #                         seriousness_points=o.seriousness_points,
# #                         next_node_key=o.next_node_key,
# #                     )
# #                     for o in n.options
# #                 ],
# #             )
# #             for n in flow.nodes
# #         ],
# #     )


# # # ============================================================
# # # ROUTES - UPDATE
# # # ============================================================
# # @router.put("/{flow_id}", response_model=dict)
# # def update_flow(
# #     flow_id: int,
# #     data: FlowUpdateIn,
# #     request: Request,
# #     db: Session = Depends(get_db),
# #     current_user: User = Depends(require_admin),
# # ):
# #     flow = (
# #         db.query(QuestionnaireFlow)
# #         .options(joinedload(QuestionnaireFlow.nodes).joinedload(FlowNode.options))
# #         .filter(
# #             QuestionnaireFlow.id == flow_id,
# #             QuestionnaireFlow.is_deleted == False,  # noqa: E712
# #         )
# #         .first()
# #     )

# #     if not flow:
# #         raise HTTPException(404, "Flow not found")

# #     normalized_nodes = normalize_nodes_for_type(data.nodes)

# #     # ✅ ORM-safe delete (cascades options too)
# #     flow.nodes.clear()
# #     db.flush()

# #     flow.name = data.name
# #     flow.description = data.description
# #     flow.flow_type = data.flow_type
# #     flow.status = data.status
# #     flow.start_node_key = data.start_node_key
# #     flow.version += 1
# #     flow.updated_at = datetime.utcnow()

# #     db.flush()

# #     created_nodes = _create_nodes_from_data(flow.id, normalized_nodes, db)
# #     errors = validate_flow_integrity(flow, created_nodes)
# #     if errors:
# #         db.rollback()
# #         raise HTTPException(400, detail={"errors": errors})

# #     db.commit()
# #     db.refresh(flow)

# #     write_audit_log(
# #         db,
# #         "FLOW_UPDATED",
# #         user_id=current_user.id,
# #         request=request,
# #         details=f"flow_id={flow.id}, version={flow.version}",
# #     )
# #     return {"flow_id": flow.id, "version": flow.version, "message": "Flow updated successfully"}


# # # ============================================================
# # # ROUTES - DELETE
# # # ============================================================
# # @router.delete("/{flow_id}", response_model=dict)
# # def delete_flow(
# #     flow_id: int,
# #     request: Request,
# #     db: Session = Depends(get_db),
# #     current_user: User = Depends(require_admin),
# # ):
# #     flow = (
# #         db.query(QuestionnaireFlow)
# #         .filter(
# #             QuestionnaireFlow.id == flow_id,
# #             QuestionnaireFlow.is_deleted == False,  # noqa: E712
# #         )
# #         .first()
# #     )

# #     if not flow:
# #         raise HTTPException(404, "Flow not found")

# #     flow.is_deleted = True
# #     db.commit()

# #     write_audit_log(db, "FLOW_DELETED", user_id=current_user.id, request=request, details=f"flow_id={flow.id}")
# #     return {"message": "Flow deleted successfully"}


# # # ============================================================
# # # ROUTES - VALIDATE
# # # ============================================================
# # @router.get("/{flow_id}/validate", response_model=dict)
# # def validate_flow(
# #     flow_id: int,
# #     db: Session = Depends(get_db),
# #     current_user: User = Depends(require_admin),
# # ):
# #     flow = (
# #         db.query(QuestionnaireFlow)
# #         .options(joinedload(QuestionnaireFlow.nodes).joinedload(FlowNode.options))
# #         .filter(
# #             QuestionnaireFlow.id == flow_id,
# #             QuestionnaireFlow.is_deleted == False,  # noqa: E712
# #         )
# #         .first()
# #     )

# #     if not flow:
# #         raise HTTPException(404, "Flow not found")

# #     errors = validate_flow_integrity(flow, flow.nodes)
# #     return {"flow_id": flow.id, "valid": len(errors) == 0, "errors": errors}


# # flows.py
# from __future__ import annotations

# from datetime import datetime
# from enum import Enum
# from typing import Optional, List, Dict, Set

# from fastapi import APIRouter, Depends, HTTPException, Request
# from pydantic import BaseModel, Field
# from sqlalchemy import (
#     Column,
#     Integer,
#     String,
#     Text,
#     DateTime,
#     ForeignKey,
#     Boolean,
#     Index,
#     UniqueConstraint,
#     Enum as SAEnum,
# )
# from sqlalchemy.orm import Session, relationship, joinedload

# from db import Base
# from auth import get_db, require_admin, write_audit_log
# from user import User

# router = APIRouter(prefix="/flows", tags=["Flows"])


# # ============================================================
# # ENUMS
# # ============================================================
# class FlowStatus(str, Enum):
#     DRAFT = "DRAFT"
#     ACTIVE = "ACTIVE"
#     ARCHIVED = "ARCHIVED"


# class FlowNodeType(str, Enum):
#     QUESTION = "QUESTION"
#     MESSAGE = "MESSAGE"
#     ALERT = "ALERT"


# class SeverityLevel(str, Enum):
#     GREEN = "GREEN"
#     AMBER = "AMBER"
#     RED = "RED"


# # ============================================================
# # CATEGORY CONSTANTS (fixed: only 2)
# # ============================================================
# CATEGORY_CLINICAL_OBS_COLORECTAL = 1
# CATEGORY_SYMPTOMS_AND_SIGNS = 2
# ALLOWED_CATEGORIES = {CATEGORY_CLINICAL_OBS_COLORECTAL, CATEGORY_SYMPTOMS_AND_SIGNS}


# # ============================================================
# # SQLALCHEMY MODELS
# # ============================================================
# class QuestionnaireFlow(Base):
#     __tablename__ = "questionnaire_flows"

#     id = Column(Integer, primary_key=True)
#     name = Column(String(200), nullable=False, index=True)
#     description = Column(Text, nullable=True)
#     flow_type = Column(String(50), nullable=False, index=True)
#     status = Column(SAEnum(FlowStatus), nullable=False, default=FlowStatus.DRAFT, index=True)

#     start_node_key = Column(String(50), nullable=False)

#     version = Column(Integer, default=1, nullable=False)
#     parent_flow_id = Column(Integer, ForeignKey("questionnaire_flows.id"), nullable=True)

#     is_deleted = Column(Boolean, default=False, nullable=False, index=True)

#     created_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
#     created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
#     updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

#     created_by = relationship("User", foreign_keys=[created_by_user_id])
#     parent_flow = relationship("QuestionnaireFlow", remote_side=[id], foreign_keys=[parent_flow_id])

#     nodes = relationship(
#         "FlowNode",
#         back_populates="flow",
#         cascade="all, delete-orphan",
#         order_by="FlowNode.display_order",
#     )


# class FlowNode(Base):
#     __tablename__ = "flow_nodes"
#     __table_args__ = (
#         UniqueConstraint("flow_id", "node_key", name="uq_flow_node_key"),
#         Index("idx_flow_node_flow", "flow_id"),
#         Index("idx_flow_node_key", "node_key"),
#         Index("idx_flow_node_type", "node_type"),
#         Index("idx_flow_node_category", "category"),
#     )

#     id = Column(Integer, primary_key=True)
#     flow_id = Column(Integer, ForeignKey("questionnaire_flows.id", ondelete="CASCADE"), nullable=False)

#     node_key = Column(String(50), nullable=False)
#     node_type = Column(SAEnum(FlowNodeType), nullable=False)

#     # ✅ Category grouping layer (fixed: 1 or 2). DB migration already added this column.
#     category = Column(Integer, nullable=False, default=CATEGORY_CLINICAL_OBS_COLORECTAL)

#     title = Column(String(200), nullable=True)
#     body_text = Column(Text, nullable=False)
#     help_text = Column(Text, nullable=True)

#     parent_node_key = Column(String(50), nullable=True)

#     depth_level = Column(Integer, default=0, nullable=False)
#     display_order = Column(Integer, default=0, nullable=False)

#     default_next_node_key = Column(String(50), nullable=True)
#     auto_next_node_key = Column(String(50), nullable=True)

#     ui_ack_required = Column(Boolean, default=False, nullable=False)

#     alert_severity = Column(SAEnum(SeverityLevel), nullable=True)
#     notify_admin = Column(Boolean, default=False, nullable=False)

#     flow = relationship("QuestionnaireFlow", back_populates="nodes")
#     options = relationship(
#         "FlowNodeOption",
#         back_populates="node",
#         cascade="all, delete-orphan",
#         order_by="FlowNodeOption.display_order",
#     )


# class FlowNodeOption(Base):
#     __tablename__ = "flow_node_options"

#     id = Column(Integer, primary_key=True)
#     node_id = Column(Integer, ForeignKey("flow_nodes.id", ondelete="CASCADE"), nullable=False, index=True)

#     display_order = Column(Integer, default=0, nullable=False)
#     label = Column(String(200), nullable=False)
#     value = Column(String(200), nullable=False)

#     severity = Column(SAEnum(SeverityLevel), default=SeverityLevel.GREEN, nullable=False)
#     news2_score = Column(Integer, default=0, nullable=False)
#     seriousness_points = Column(Integer, default=0, nullable=False)

#     next_node_key = Column(String(50), nullable=True)

#     node = relationship("FlowNode", back_populates="options")


# # ============================================================
# # PYDANTIC SCHEMAS
# # ============================================================
# class FlowOptionIn(BaseModel):
#     display_order: int
#     label: str
#     value: str
#     severity: SeverityLevel
#     news2_score: int = 0
#     seriousness_points: int = 0
#     next_node_key: Optional[str] = None


# class FlowNodeIn(BaseModel):
#     node_key: str
#     node_type: FlowNodeType

#     # ✅ Category included in payload. Default = 1 for backwards compatibility.
#     category: int = Field(default=CATEGORY_CLINICAL_OBS_COLORECTAL)

#     title: Optional[str] = None
#     body_text: str
#     help_text: Optional[str] = None
#     parent_node_key: Optional[str] = None
#     default_next_node_key: Optional[str] = None
#     auto_next_node_key: Optional[str] = None
#     ui_ack_required: bool = False
#     alert_severity: Optional[SeverityLevel] = None
#     notify_admin: bool = False
#     options: List[FlowOptionIn] = Field(default_factory=list)


# class FlowCreateIn(BaseModel):
#     name: str = Field(min_length=1, max_length=200)
#     description: Optional[str] = None
#     flow_type: str = Field(min_length=1, max_length=50)
#     status: FlowStatus = FlowStatus.DRAFT
#     start_node_key: str
#     nodes: List[FlowNodeIn] = Field(min_items=1)


# class FlowUpdateIn(BaseModel):
#     name: str = Field(min_length=1, max_length=200)
#     description: Optional[str] = None
#     flow_type: str = Field(min_length=1, max_length=50)
#     status: FlowStatus
#     start_node_key: str
#     nodes: List[FlowNodeIn] = Field(min_items=1)


# class FlowOptionOut(BaseModel):
#     id: int
#     display_order: int
#     label: str
#     value: str
#     severity: str
#     news2_score: int
#     seriousness_points: int
#     next_node_key: Optional[str]

#     class Config:
#         from_attributes = True


# class FlowNodeOut(BaseModel):
#     id: int
#     node_key: str
#     node_type: str

#     # ✅ Category returned
#     category: int

#     title: Optional[str]
#     body_text: str
#     help_text: Optional[str]
#     parent_node_key: Optional[str]
#     depth_level: int
#     default_next_node_key: Optional[str]
#     auto_next_node_key: Optional[str]
#     ui_ack_required: bool
#     alert_severity: Optional[str]
#     notify_admin: bool
#     options: List[FlowOptionOut]

#     class Config:
#         from_attributes = True


# class FlowDetailOut(BaseModel):
#     id: int
#     name: str
#     description: Optional[str]
#     flow_type: str
#     status: str
#     start_node_key: str
#     version: int
#     created_at: datetime
#     updated_at: datetime
#     created_by: dict
#     nodes: List[FlowNodeOut]

#     class Config:
#         from_attributes = True


# class FlowOut(BaseModel):
#     id: int
#     name: str
#     description: Optional[str]
#     flow_type: str
#     status: str
#     start_node_key: str
#     version: int
#     node_count: int
#     created_at: datetime
#     created_by: dict

#     class Config:
#         from_attributes = True


# class FlowListOut(BaseModel):
#     total: int
#     items: List[FlowOut]


# # ============================================================
# # NORMALIZE INPUT
# # ============================================================
# def normalize_nodes_for_type(nodes: List[FlowNodeIn]) -> List[FlowNodeIn]:
#     """
#     MESSAGE/ALERT safe defaults:
#     - force options=[]
#     - clear default_next_node_key
#     - ensure auto_next_node_key (default END)
#     - ALERT default severity RED
#     """
#     normalized: List[FlowNodeIn] = []

#     for n in nodes:
#         if n.node_type in (FlowNodeType.MESSAGE, FlowNodeType.ALERT):
#             normalized.append(
#                 FlowNodeIn(
#                     node_key=n.node_key,
#                     node_type=n.node_type,
#                     category=n.category,  # ✅ preserve category
#                     title=n.title,
#                     body_text=n.body_text,
#                     help_text=n.help_text,
#                     parent_node_key=n.parent_node_key,
#                     default_next_node_key=None,
#                     auto_next_node_key=n.auto_next_node_key or "END",
#                     ui_ack_required=n.ui_ack_required,
#                     alert_severity=(n.alert_severity or SeverityLevel.RED) if n.node_type == FlowNodeType.ALERT else None,
#                     notify_admin=bool(n.notify_admin) if n.node_type == FlowNodeType.ALERT else False,
#                     options=[],
#                 )
#             )
#         else:
#             normalized.append(n)

#     return normalized


# # ============================================================
# # VALIDATION
# # ============================================================
# def validate_flow_integrity(flow: QuestionnaireFlow, nodes: List[FlowNode]) -> List[str]:
#     errors: List[str] = []
#     if not nodes:
#         return ["Flow must have at least one node"]

#     node_by_key: Dict[str, FlowNode] = {n.node_key: n for n in nodes}
#     node_keys = set(node_by_key.keys())

#     if flow.start_node_key not in node_keys:
#         errors.append(f"start_node_key '{flow.start_node_key}' not found")

#     # ---------------- Category validation ----------------
#     for n in nodes:
#         if n.category not in ALLOWED_CATEGORIES:
#             errors.append(f"Node '{n.node_key}': category must be 1 or 2")

#     # Parent-child category match
#     for n in nodes:
#         if not n.parent_node_key:
#             continue
#         parent = node_by_key.get(n.parent_node_key)
#         if not parent:
#             # parent missing is not necessarily fatal for validation, but it's usually a modeling error
#             errors.append(f"Node '{n.node_key}': parent_node_key '{n.parent_node_key}' not found")
#             continue
#         if n.category != parent.category:
#             errors.append(
#                 f"Node '{n.node_key}': category ({n.category}) must match parent '{parent.node_key}' category ({parent.category})"
#             )

#     # Helper: check next-node category consistency
#     def check_next_same_category(src_key: str, dst_key: Optional[str], relation: str):
#         if not dst_key or dst_key == "END":
#             return
#         dst = node_by_key.get(dst_key)
#         if not dst:
#             return
#         src = node_by_key.get(src_key)
#         if not src:
#             return
#         if src.category != dst.category:
#             errors.append(
#                 f"Node '{src_key}': {relation} '{dst_key}' must be in same category (src={src.category}, dst={dst.category})"
#             )

#     # ---------------- Existing node-type validation ----------------
#     for node in nodes:
#         if node.node_type == FlowNodeType.QUESTION:
#             if not node.options or len(node.options) < 2:
#                 errors.append(f"Node '{node.node_key}': QUESTION must have >= 2 options")

#             if node.default_next_node_key and node.default_next_node_key != "END" and node.default_next_node_key not in node_keys:
#                 errors.append(f"Node '{node.node_key}': invalid default_next_node_key")
#             else:
#                 # ✅ enforce same-category next
#                 check_next_same_category(node.node_key, node.default_next_node_key, "default_next_node_key")

#             for opt in node.options:
#                 if opt.next_node_key and opt.next_node_key != "END" and opt.next_node_key not in node_keys:
#                     errors.append(f"Node '{node.node_key}', option '{opt.label}': invalid next_node_key")
#                 else:
#                     # ✅ enforce same-category option next
#                     check_next_same_category(node.node_key, opt.next_node_key, "option next_node_key")

#         elif node.node_type in (FlowNodeType.MESSAGE, FlowNodeType.ALERT):
#             if not node.auto_next_node_key:
#                 errors.append(f"Node '{node.node_key}': {node.node_type.value} must have auto_next_node_key")
#             elif node.auto_next_node_key != "END" and node.auto_next_node_key not in node_keys:
#                 errors.append(f"Node '{node.node_key}': invalid auto_next_node_key")
#             else:
#                 # ✅ enforce same-category next
#                 check_next_same_category(node.node_key, node.auto_next_node_key, "auto_next_node_key")

#             if node.options and len(node.options) > 0:
#                 errors.append(f"Node '{node.node_key}': {node.node_type.value} must not have options")

#             if node.node_type == FlowNodeType.ALERT and not node.alert_severity:
#                 errors.append(f"Node '{node.node_key}': ALERT must have alert_severity")

#     # ---------------- Standard DFS cycle detection ----------------
#     graph: Dict[str, List[str]] = {}

#     def add_edge(src: str, dst: Optional[str]):
#         if not dst:
#             return
#         graph.setdefault(src, [])
#         graph[src].append(dst)

#     for n in nodes:
#         if n.node_type == FlowNodeType.QUESTION:
#             add_edge(n.node_key, n.default_next_node_key)
#             for o in n.options:
#                 add_edge(n.node_key, o.next_node_key)
#         else:
#             add_edge(n.node_key, n.auto_next_node_key)

#     visited: Set[str] = set()
#     stack: Set[str] = set()

#     def dfs(u: str) -> bool:
#         if u == "END":
#             return False
#         if u in stack:
#             return True
#         if u in visited:
#             return False
#         visited.add(u)
#         stack.add(u)
#         for v in graph.get(u, []):
#             if dfs(v):
#                 return True
#         stack.remove(u)
#         return False

#     if flow.start_node_key in node_keys and dfs(flow.start_node_key):
#         errors.append("Flow contains cycles")

#     return errors


# # ============================================================
# # HELPER
# # ============================================================
# def _create_nodes_from_data(flow_id: int, nodes_data: List[FlowNodeIn], db: Session) -> List[FlowNode]:
#     created_nodes: List[FlowNode] = []

#     for idx, node_data in enumerate(nodes_data):
#         node = FlowNode(
#             flow_id=flow_id,
#             node_key=node_data.node_key,
#             node_type=node_data.node_type,
#             category=node_data.category or CATEGORY_CLINICAL_OBS_COLORECTAL,  # ✅ persist category (default=1)
#             title=node_data.title,
#             body_text=node_data.body_text,
#             help_text=node_data.help_text,
#             parent_node_key=node_data.parent_node_key,
#             depth_level=node_data.node_key.count("."),
#             display_order=idx,
#             default_next_node_key=node_data.default_next_node_key,
#             auto_next_node_key=node_data.auto_next_node_key,
#             ui_ack_required=node_data.ui_ack_required,
#             alert_severity=node_data.alert_severity,
#             notify_admin=node_data.notify_admin,
#         )

#         for opt_data in (node_data.options or []):
#             node.options.append(
#                 FlowNodeOption(
#                     display_order=opt_data.display_order,
#                     label=opt_data.label,
#                     value=opt_data.value,
#                     severity=opt_data.severity,
#                     news2_score=opt_data.news2_score,
#                     seriousness_points=opt_data.seriousness_points,
#                     next_node_key=opt_data.next_node_key,
#                 )
#             )

#         db.add(node)
#         created_nodes.append(node)

#     db.flush()
#     return created_nodes


# def _safe_user_name(u: Optional[User]) -> str:
#     if not u:
#         return ""
#     return (getattr(u, "name", None) or getattr(u, "full_name", None) or "").strip()


# # ============================================================
# # ROUTES - CREATE
# # ============================================================
# @router.post("/", response_model=dict)
# def create_flow(
#     data: FlowCreateIn,
#     request: Request,
#     db: Session = Depends(get_db),
#     current_user: User = Depends(require_admin),
# ):
#     normalized_nodes = normalize_nodes_for_type(data.nodes)

#     flow = QuestionnaireFlow(
#         name=data.name,
#         description=data.description,
#         flow_type=data.flow_type,
#         status=data.status,
#         start_node_key=data.start_node_key,
#         version=1,
#         created_by_user_id=current_user.id,
#     )
#     db.add(flow)
#     db.flush()

#     created_nodes = _create_nodes_from_data(flow.id, normalized_nodes, db)
#     errors = validate_flow_integrity(flow, created_nodes)
#     if errors:
#         db.rollback()
#         raise HTTPException(400, detail={"errors": errors})

#     db.commit()
#     db.refresh(flow)

#     write_audit_log(db, "FLOW_CREATED", user_id=current_user.id, request=request, details=f"flow_id={flow.id}")
#     return {"flow_id": flow.id, "message": "Flow created successfully"}


# # ============================================================
# # ROUTES - LIST
# # ============================================================
# @router.get("/", response_model=FlowListOut)
# def list_flows(
#     db: Session = Depends(get_db),
#     current_user: User = Depends(require_admin),
#     q: Optional[str] = None,
#     flow_type: Optional[str] = None,
#     status: Optional[FlowStatus] = None,
#     skip: int = 0,
#     limit: int = 20,
# ):
#     query = (
#         db.query(QuestionnaireFlow)
#         .options(joinedload(QuestionnaireFlow.created_by))
#         .filter(QuestionnaireFlow.is_deleted == False)  # noqa: E712
#     )

#     if q:
#         query = query.filter(QuestionnaireFlow.name.ilike(f"%{q.strip()}%"))
#     if flow_type:
#         query = query.filter(QuestionnaireFlow.flow_type == flow_type)
#     if status:
#         query = query.filter(QuestionnaireFlow.status == status)

#     total = query.count()
#     flows = (
#         query.order_by(QuestionnaireFlow.created_at.desc())
#         .offset(skip)
#         .limit(min(limit, 100))
#         .all()
#     )

#     items: List[FlowOut] = []
#     for f in flows:
#         items.append(
#             FlowOut(
#                 id=f.id,
#                 name=f.name,
#                 description=f.description,
#                 flow_type=f.flow_type,
#                 status=f.status.value,
#                 start_node_key=f.start_node_key,
#                 version=f.version,
#                 node_count=db.query(FlowNode).filter(FlowNode.flow_id == f.id).count(),
#                 created_at=f.created_at,
#                 created_by={
#                     "id": f.created_by.id if f.created_by else None,
#                     "name": _safe_user_name(f.created_by),
#                     "email": getattr(f.created_by, "email", "") if f.created_by else "",
#                 },
#             )
#         )

#     return FlowListOut(total=total, items=items)


# # ============================================================
# # ROUTES - GET DETAIL
# # ============================================================
# @router.get("/{flow_id}", response_model=FlowDetailOut)
# def get_flow(
#     flow_id: int,
#     db: Session = Depends(get_db),
#     current_user: User = Depends(require_admin),
# ):
#     flow = (
#         db.query(QuestionnaireFlow)
#         .options(
#             joinedload(QuestionnaireFlow.created_by),
#             joinedload(QuestionnaireFlow.nodes).joinedload(FlowNode.options),
#         )
#         .filter(
#             QuestionnaireFlow.id == flow_id,
#             QuestionnaireFlow.is_deleted == False,  # noqa: E712
#         )
#         .first()
#     )

#     if not flow:
#         raise HTTPException(404, "Flow not found")

#     return FlowDetailOut(
#         id=flow.id,
#         name=flow.name,
#         description=flow.description,
#         flow_type=flow.flow_type,
#         status=flow.status.value,
#         start_node_key=flow.start_node_key,
#         version=flow.version,
#         created_at=flow.created_at,
#         updated_at=flow.updated_at,
#         created_by={
#             "id": flow.created_by.id if flow.created_by else None,
#             "name": _safe_user_name(flow.created_by),
#             "email": getattr(flow.created_by, "email", "") if flow.created_by else "",
#         },
#         nodes=[
#             FlowNodeOut(
#                 id=n.id,
#                 node_key=n.node_key,
#                 node_type=n.node_type.value,
#                 category=n.category,  # ✅ include category
#                 title=n.title,
#                 body_text=n.body_text,
#                 help_text=n.help_text,
#                 parent_node_key=n.parent_node_key,
#                 depth_level=n.depth_level,
#                 default_next_node_key=n.default_next_node_key,
#                 auto_next_node_key=n.auto_next_node_key,
#                 ui_ack_required=n.ui_ack_required,
#                 alert_severity=n.alert_severity.value if n.alert_severity else None,
#                 notify_admin=n.notify_admin,
#                 options=[
#                     FlowOptionOut(
#                         id=o.id,
#                         display_order=o.display_order,
#                         label=o.label,
#                         value=o.value,
#                         severity=o.severity.value,
#                         news2_score=o.news2_score,
#                         seriousness_points=o.seriousness_points,
#                         next_node_key=o.next_node_key,
#                     )
#                     for o in n.options
#                 ],
#             )
#             for n in flow.nodes
#         ],
#     )


# # ============================================================
# # ROUTES - UPDATE
# # ============================================================
# @router.put("/{flow_id}", response_model=dict)
# def update_flow(
#     flow_id: int,
#     data: FlowUpdateIn,
#     request: Request,
#     db: Session = Depends(get_db),
#     current_user: User = Depends(require_admin),
# ):
#     flow = (
#         db.query(QuestionnaireFlow)
#         .options(joinedload(QuestionnaireFlow.nodes).joinedload(FlowNode.options))
#         .filter(
#             QuestionnaireFlow.id == flow_id,
#             QuestionnaireFlow.is_deleted == False,  # noqa: E712
#         )
#         .first()
#     )

#     if not flow:
#         raise HTTPException(404, "Flow not found")

#     normalized_nodes = normalize_nodes_for_type(data.nodes)

#     # ✅ ORM-safe delete (cascades options too)
#     flow.nodes.clear()
#     db.flush()

#     flow.name = data.name
#     flow.description = data.description
#     flow.flow_type = data.flow_type
#     flow.status = data.status
#     flow.start_node_key = data.start_node_key
#     flow.version += 1
#     flow.updated_at = datetime.utcnow()

#     db.flush()

#     created_nodes = _create_nodes_from_data(flow.id, normalized_nodes, db)
#     errors = validate_flow_integrity(flow, created_nodes)
#     if errors:
#         db.rollback()
#         raise HTTPException(400, detail={"errors": errors})

#     db.commit()
#     db.refresh(flow)

#     write_audit_log(
#         db,
#         "FLOW_UPDATED",
#         user_id=current_user.id,
#         request=request,
#         details=f"flow_id={flow.id}, version={flow.version}",
#     )
#     return {"flow_id": flow.id, "version": flow.version, "message": "Flow updated successfully"}


# # ============================================================
# # ROUTES - DELETE
# # ============================================================
# @router.delete("/{flow_id}", response_model=dict)
# def delete_flow(
#     flow_id: int,
#     request: Request,
#     db: Session = Depends(get_db),
#     current_user: User = Depends(require_admin),
# ):
#     flow = (
#         db.query(QuestionnaireFlow)
#         .filter(
#             QuestionnaireFlow.id == flow_id,
#             QuestionnaireFlow.is_deleted == False,  # noqa: E712
#         )
#         .first()
#     )

#     if not flow:
#         raise HTTPException(404, "Flow not found")

#     flow.is_deleted = True
#     db.commit()

#     write_audit_log(db, "FLOW_DELETED", user_id=current_user.id, request=request, details=f"flow_id={flow.id}")
#     return {"message": "Flow deleted successfully"}


# # ============================================================
# # ROUTES - VALIDATE
# # ============================================================
# @router.get("/{flow_id}/validate", response_model=dict)
# def validate_flow(
#     flow_id: int,
#     db: Session = Depends(get_db),
#     current_user: User = Depends(require_admin),
# ):
#     flow = (
#         db.query(QuestionnaireFlow)
#         .options(joinedload(QuestionnaireFlow.nodes).joinedload(FlowNode.options))
#         .filter(
#             QuestionnaireFlow.id == flow_id,
#             QuestionnaireFlow.is_deleted == False,  # noqa: E712
#         )
#         .first()
#     )

#     if not flow:
#         raise HTTPException(404, "Flow not found")

#     errors = validate_flow_integrity(flow, flow.nodes)
#     return {"flow_id": flow.id, "valid": len(errors) == 0, "errors": errors}


# # from __future__ import annotations

# # from datetime import datetime
# # from enum import Enum
# # from typing import Optional, List

# # from fastapi import APIRouter, Depends, HTTPException, Request
# # from pydantic import BaseModel, Field
# # from sqlalchemy import (
# #     Column,
# #     Integer,
# #     String,
# #     Text,
# #     DateTime,
# #     ForeignKey,
# #     Boolean,
# #     Index,
# #     UniqueConstraint,
# #     Enum as SAEnum,
# # )
# # from sqlalchemy.orm import Session, relationship, joinedload

# # from db import Base
# # from auth import get_db, require_admin, write_audit_log
# # from user import User

# # router = APIRouter(prefix="/flows", tags=["Flows"])

# # # ============================================================
# # # ENUMS
# # # ============================================================
# # class FlowStatus(str, Enum):
# #     DRAFT = "DRAFT"
# #     ACTIVE = "ACTIVE"
# #     ARCHIVED = "ARCHIVED"


# # class FlowNodeType(str, Enum):
# #     QUESTION = "QUESTION"
# #     MESSAGE = "MESSAGE"
# #     ALERT = "ALERT"


# # class SeverityLevel(str, Enum):
# #     GREEN = "GREEN"
# #     AMBER = "AMBER"
# #     RED = "RED"


# # # ============================================================
# # # SQLALCHEMY MODELS
# # # ============================================================
# # class QuestionnaireFlow(Base):
# #     __tablename__ = "questionnaire_flows"
# #     id = Column(Integer, primary_key=True)
# #     name = Column(String(200), nullable=False, index=True)
# #     description = Column(Text, nullable=True)
# #     flow_type = Column(String(50), nullable=False, index=True)
# #     status = Column(SAEnum(FlowStatus), nullable=False, default=FlowStatus.DRAFT, index=True)
# #     start_node_key = Column(String(50), nullable=False)
# #     version = Column(Integer, default=1, nullable=False)
# #     parent_flow_id = Column(Integer, ForeignKey("questionnaire_flows.id"), nullable=True)
# #     is_deleted = Column(Boolean, default=False, nullable=False, index=True)
# #     created_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
# #     created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
# #     updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

# #     created_by = relationship("User", foreign_keys=[created_by_user_id])
# #     parent_flow = relationship("QuestionnaireFlow", remote_side=[id], foreign_keys=[parent_flow_id])
# #     nodes = relationship(
# #         "FlowNode",
# #         back_populates="flow",
# #         cascade="all, delete-orphan",
# #         order_by="FlowNode.display_order",
# #     )


# # class FlowNode(Base):
# #     __tablename__ = "flow_nodes"
# #     __table_args__ = (
# #         UniqueConstraint("flow_id", "node_key", name="uq_flow_node_key"),
# #         Index("idx_flow_node_flow", "flow_id"),
# #         Index("idx_flow_node_key", "node_key"),
# #         Index("idx_flow_node_type", "node_type"),
# #     )

# #     id = Column(Integer, primary_key=True)
# #     flow_id = Column(Integer, ForeignKey("questionnaire_flows.id", ondelete="CASCADE"), nullable=False)
# #     node_key = Column(String(50), nullable=False)
# #     node_type = Column(SAEnum(FlowNodeType), nullable=False)
# #     title = Column(String(200), nullable=True)
# #     body_text = Column(Text, nullable=False)
# #     help_text = Column(Text, nullable=True)
# #     parent_node_key = Column(String(50), nullable=True)
# #     depth_level = Column(Integer, default=0, nullable=False)
# #     display_order = Column(Integer, default=0, nullable=False)
# #     default_next_node_key = Column(String(50), nullable=True)
# #     auto_next_node_key = Column(String(50), nullable=True)
# #     ui_ack_required = Column(Boolean, default=False, nullable=False)
# #     alert_severity = Column(SAEnum(SeverityLevel), nullable=True)
# #     notify_admin = Column(Boolean, default=False, nullable=False)

# #     flow = relationship("QuestionnaireFlow", back_populates="nodes")
# #     options = relationship(
# #         "FlowNodeOption",
# #         back_populates="node",
# #         cascade="all, delete-orphan",
# #         order_by="FlowNodeOption.display_order",
# #     )


# # class FlowNodeOption(Base):
# #     __tablename__ = "flow_node_options"
# #     id = Column(Integer, primary_key=True)
# #     node_id = Column(Integer, ForeignKey("flow_nodes.id", ondelete="CASCADE"), nullable=False, index=True)
# #     display_order = Column(Integer, default=0, nullable=False)
# #     label = Column(String(200), nullable=False)
# #     value = Column(String(200), nullable=False)
# #     severity = Column(SAEnum(SeverityLevel), default=SeverityLevel.GREEN, nullable=False)
# #     news2_score = Column(Integer, default=0, nullable=False)
# #     seriousness_points = Column(Integer, default=0, nullable=False)
# #     next_node_key = Column(String(50), nullable=True)

# #     node = relationship("FlowNode", back_populates="options")


# # # ============================================================
# # # PYDANTIC SCHEMAS
# # # ============================================================
# # class FlowOptionIn(BaseModel):
# #     display_order: int
# #     label: str
# #     value: str
# #     severity: SeverityLevel
# #     news2_score: int = 0
# #     seriousness_points: int = 0
# #     next_node_key: Optional[str] = None


# # class FlowNodeIn(BaseModel):
# #     node_key: str
# #     node_type: FlowNodeType
# #     title: Optional[str] = None
# #     body_text: str
# #     help_text: Optional[str] = None
# #     parent_node_key: Optional[str] = None
# #     default_next_node_key: Optional[str] = None
# #     auto_next_node_key: Optional[str] = None
# #     ui_ack_required: bool = False
# #     alert_severity: Optional[SeverityLevel] = None
# #     notify_admin: bool = False
# #     options: List[FlowOptionIn] = []


# # class FlowCreateIn(BaseModel):
# #     name: str = Field(min_length=1, max_length=200)
# #     description: Optional[str] = None
# #     flow_type: str = Field(min_length=1, max_length=50)
# #     status: FlowStatus = FlowStatus.DRAFT
# #     start_node_key: str
# #     nodes: List[FlowNodeIn] = Field(min_items=1)


# # class FlowUpdateIn(BaseModel):
# #     name: str = Field(min_length=1, max_length=200)
# #     description: Optional[str] = None
# #     flow_type: str = Field(min_length=1, max_length=50)
# #     status: FlowStatus
# #     start_node_key: str
# #     nodes: List[FlowNodeIn] = Field(min_items=1)


# # class FlowOptionOut(BaseModel):
# #     id: int
# #     display_order: int
# #     label: str
# #     value: str
# #     severity: str
# #     news2_score: int
# #     seriousness_points: int
# #     next_node_key: Optional[str]

# #     class Config:
# #         from_attributes = True


# # class FlowNodeOut(BaseModel):
# #     id: int
# #     node_key: str
# #     node_type: str
# #     title: Optional[str]
# #     body_text: str
# #     help_text: Optional[str]
# #     parent_node_key: Optional[str]
# #     depth_level: int
# #     default_next_node_key: Optional[str]
# #     auto_next_node_key: Optional[str]
# #     ui_ack_required: bool
# #     alert_severity: Optional[str]
# #     notify_admin: bool
# #     options: List[FlowOptionOut]

# #     class Config:
# #         from_attributes = True


# # class FlowDetailOut(BaseModel):
# #     id: int
# #     name: str
# #     description: Optional[str]
# #     flow_type: str
# #     status: str
# #     start_node_key: str
# #     version: int
# #     created_at: datetime
# #     updated_at: datetime
# #     created_by: dict
# #     nodes: List[FlowNodeOut]

# #     class Config:
# #         from_attributes = True


# # class FlowOut(BaseModel):
# #     id: int
# #     name: str
# #     description: Optional[str]
# #     flow_type: str
# #     status: str
# #     start_node_key: str
# #     version: int
# #     node_count: int
# #     created_at: datetime
# #     created_by: dict

# #     class Config:
# #         from_attributes = True


# # class FlowListOut(BaseModel):
# #     total: int
# #     items: List[FlowOut]


# # # ============================================================
# # # NORMALIZE INPUT (✅ MINIMAL BUT IMPORTANT)
# # # ============================================================
# # def normalize_nodes_for_type(nodes: List[FlowNodeIn]) -> List[FlowNodeIn]:
# #     """
# #     Makes MESSAGE/ALERT safe even if frontend forgets:
# #     - MESSAGE/ALERT must have auto_next_node_key (default END)
# #     - MESSAGE/ALERT should not have options/default_next_node_key
# #     - ALERT should have alert_severity (default RED)
# #     """
# #     normalized: List[FlowNodeIn] = []

# #     for n in nodes:
# #         if n.node_type in (FlowNodeType.MESSAGE, FlowNodeType.ALERT):
# #             normalized.append(
# #                 FlowNodeIn(
# #                     node_key=n.node_key,
# #                     node_type=n.node_type,
# #                     title=n.title,
# #                     body_text=n.body_text,
# #                     help_text=n.help_text,
# #                     parent_node_key=n.parent_node_key,
# #                     default_next_node_key=None,
# #                     auto_next_node_key=n.auto_next_node_key or "END",
# #                     ui_ack_required=n.ui_ack_required,
# #                     alert_severity=(n.alert_severity or SeverityLevel.RED)
# #                     if n.node_type == FlowNodeType.ALERT
# #                     else None,
# #                     notify_admin=bool(n.notify_admin) if n.node_type == FlowNodeType.ALERT else False,
# #                     options=[],  # ✅ force empty
# #                 )
# #             )
# #         else:
# #             # QUESTION: keep as-is
# #             normalized.append(n)

# #     return normalized


# # # ============================================================
# # # VALIDATION
# # # ============================================================
# # def validate_flow_integrity(flow: QuestionnaireFlow, nodes: List[FlowNode]) -> List[str]:
# #     errors = []
# #     if not nodes:
# #         errors.append("Flow must have at least one node")
# #         return errors

# #     node_keys = {n.node_key for n in nodes}
# #     if flow.start_node_key not in node_keys:
# #         errors.append(f"start_node_key '{flow.start_node_key}' not found")

# #     for node in nodes:
# #         if node.node_type == FlowNodeType.QUESTION:
# #             if not node.options or len(node.options) < 2:
# #                 errors.append(f"Node '{node.node_key}': QUESTION must have >= 2 options")
# #             if (
# #                 node.default_next_node_key
# #                 and node.default_next_node_key != "END"
# #                 and node.default_next_node_key not in node_keys
# #             ):
# #                 errors.append(f"Node '{node.node_key}': invalid default_next_node_key")
# #             for opt in node.options:
# #                 if opt.next_node_key and opt.next_node_key != "END" and opt.next_node_key not in node_keys:
# #                     errors.append(f"Node '{node.node_key}', option '{opt.label}': invalid next_node_key")

# #         elif node.node_type in (FlowNodeType.MESSAGE, FlowNodeType.ALERT):
# #             if not node.auto_next_node_key:
# #                 errors.append(f"Node '{node.node_key}': {node.node_type.value} must have auto_next_node_key")
# #             elif node.auto_next_node_key != "END" and node.auto_next_node_key not in node_keys:
# #                 errors.append(f"Node '{node.node_key}': invalid auto_next_node_key")

# #             # ✅ extra safety: message/alert should not have options
# #             if node.options and len(node.options) > 0:
# #                 errors.append(f"Node '{node.node_key}': {node.node_type.value} must not have options")

# #             # ✅ alert should have severity
# #             if node.node_type == FlowNodeType.ALERT and not node.alert_severity:
# #                 errors.append(f"Node '{node.node_key}': ALERT must have alert_severity")

# #     def has_cycle(current: str, visited: set, stack: set) -> bool:
# #         if current == "END" or current in visited:
# #             return current in stack
# #         visited.add(current)
# #         stack.add(current)

# #         node = next((n for n in nodes if n.node_key == current), None)
# #         if node:
# #             next_keys = []
# #             if node.node_type == FlowNodeType.QUESTION:
# #                 if node.default_next_node_key:
# #                     next_keys.append(node.default_next_node_key)
# #                 for opt in node.options:
# #                     if opt.next_node_key:
# #                         next_keys.append(opt.next_node_key)
# #             else:
# #                 if node.auto_next_node_key:
# #                     next_keys.append(node.auto_next_node_key)

# #             for nk in next_keys:
# #                 if has_cycle(nk, visited, stack):
# #                     return True

# #         stack.remove(current)
# #         return False

# #     if has_cycle(flow.start_node_key, set(), set()):
# #         errors.append("Flow contains cycles")

# #     return errors


# # # ============================================================
# # # HELPER (options attach via relationship ✅)
# # # ============================================================
# # def _create_nodes_from_data(flow_id: int, nodes_data: List[FlowNodeIn], db: Session) -> List[FlowNode]:
# #     created_nodes: List[FlowNode] = []

# #     for idx, node_data in enumerate(nodes_data):
# #         node = FlowNode(
# #             flow_id=flow_id,
# #             node_key=node_data.node_key,
# #             node_type=node_data.node_type,
# #             title=node_data.title,
# #             body_text=node_data.body_text,
# #             help_text=node_data.help_text,
# #             parent_node_key=node_data.parent_node_key,
# #             depth_level=node_data.node_key.count("."),
# #             display_order=idx,
# #             default_next_node_key=node_data.default_next_node_key,
# #             auto_next_node_key=node_data.auto_next_node_key,
# #             ui_ack_required=node_data.ui_ack_required,
# #             alert_severity=node_data.alert_severity,
# #             notify_admin=node_data.notify_admin,
# #         )

# #         for opt_data in (node_data.options or []):
# #             node.options.append(
# #                 FlowNodeOption(
# #                     display_order=opt_data.display_order,
# #                     label=opt_data.label,
# #                     value=opt_data.value,
# #                     severity=opt_data.severity,
# #                     news2_score=opt_data.news2_score,
# #                     seriousness_points=opt_data.seriousness_points,
# #                     next_node_key=opt_data.next_node_key,
# #                 )
# #             )

# #         db.add(node)
# #         created_nodes.append(node)

# #     db.flush()
# #     return created_nodes


# # # ============================================================
# # # ROUTES - CREATE
# # # ============================================================
# # @router.post("/", response_model=dict)
# # def create_flow(
# #     data: FlowCreateIn,
# #     request: Request,
# #     db: Session = Depends(get_db),
# #     current_user: User = Depends(require_admin),
# # ):
# #     # ✅ normalize nodes before creating
# #     normalized_nodes = normalize_nodes_for_type(data.nodes)

# #     flow = QuestionnaireFlow(
# #         name=data.name,
# #         description=data.description,
# #         flow_type=data.flow_type,
# #         status=data.status,
# #         start_node_key=data.start_node_key,
# #         version=1,
# #         created_by_user_id=current_user.id,
# #     )
# #     db.add(flow)
# #     db.flush()

# #     created_nodes = _create_nodes_from_data(flow.id, normalized_nodes, db)
# #     errors = validate_flow_integrity(flow, created_nodes)
# #     if errors:
# #         db.rollback()
# #         raise HTTPException(400, detail={"errors": errors})

# #     db.commit()
# #     db.refresh(flow)

# #     write_audit_log(db, "FLOW_CREATED", user_id=current_user.id, request=request, details=f"flow_id={flow.id}")
# #     return {"flow_id": flow.id, "message": "Flow created successfully"}


# # # ============================================================
# # # ROUTES - READ
# # # ============================================================
# # @router.get("/", response_model=FlowListOut)
# # def list_flows(
# #     db: Session = Depends(get_db),
# #     current_user: User = Depends(require_admin),
# #     q: Optional[str] = None,
# #     flow_type: Optional[str] = None,
# #     status: Optional[FlowStatus] = None,
# #     skip: int = 0,
# #     limit: int = 20,
# # ):
# #     query = (
# #         db.query(QuestionnaireFlow)
# #         .options(joinedload(QuestionnaireFlow.created_by))
# #         .filter(QuestionnaireFlow.is_deleted == False)  # noqa: E712
# #     )

# #     if q:
# #         query = query.filter(QuestionnaireFlow.name.ilike(f"%{q.strip()}%"))
# #     if flow_type:
# #         query = query.filter(QuestionnaireFlow.flow_type == flow_type)
# #     if status:
# #         query = query.filter(QuestionnaireFlow.status == status)

# #     total = query.count()
# #     flows = (
# #         query.order_by(QuestionnaireFlow.created_at.desc())
# #         .offset(skip)
# #         .limit(min(limit, 100))
# #         .all()
# #     )

# #     items = [
# #         FlowOut(
# #             id=f.id,
# #             name=f.name,
# #             description=f.description,
# #             flow_type=f.flow_type,
# #             status=f.status.value,
# #             start_node_key=f.start_node_key,
# #             version=f.version,
# #             node_count=db.query(FlowNode).filter(FlowNode.flow_id == f.id).count(),
# #             created_at=f.created_at,
# #             created_by={
# #                 "id": f.created_by.id,
# #                 "name": f.created_by.name,
# #                 "email": f.created_by.email,
# #             },
# #         )
# #         for f in flows
# #     ]

# #     return FlowListOut(total=total, items=items)


# # @router.get("/{flow_id}", response_model=FlowDetailOut)
# # def get_flow(
# #     flow_id: int,
# #     db: Session = Depends(get_db),
# #     current_user: User = Depends(require_admin),
# # ):
# #     flow = (
# #         db.query(QuestionnaireFlow)
# #         .options(
# #             joinedload(QuestionnaireFlow.created_by),
# #             joinedload(QuestionnaireFlow.nodes).joinedload(FlowNode.options),
# #         )
# #         .filter(
# #             QuestionnaireFlow.id == flow_id,
# #             QuestionnaireFlow.is_deleted == False,  # noqa: E712
# #         )
# #         .first()
# #     )

# #     if not flow:
# #         raise HTTPException(404, "Flow not found")

# #     return FlowDetailOut(
# #         id=flow.id,
# #         name=flow.name,
# #         description=flow.description,
# #         flow_type=flow.flow_type,
# #         status=flow.status.value,
# #         start_node_key=flow.start_node_key,
# #         version=flow.version,
# #         created_at=flow.created_at,
# #         updated_at=flow.updated_at,
# #         created_by={
# #             "id": flow.created_by.id,
# #             "name": flow.created_by.name,
# #             "email": flow.created_by.email,
# #         },
# #         nodes=[
# #             FlowNodeOut(
# #                 id=n.id,
# #                 node_key=n.node_key,
# #                 node_type=n.node_type.value,
# #                 title=n.title,
# #                 body_text=n.body_text,
# #                 help_text=n.help_text,
# #                 parent_node_key=n.parent_node_key,
# #                 depth_level=n.depth_level,
# #                 default_next_node_key=n.default_next_node_key,
# #                 auto_next_node_key=n.auto_next_node_key,
# #                 ui_ack_required=n.ui_ack_required,
# #                 alert_severity=n.alert_severity.value if n.alert_severity else None,
# #                 notify_admin=n.notify_admin,
# #                 options=[
# #                     FlowOptionOut(
# #                         id=o.id,
# #                         display_order=o.display_order,
# #                         label=o.label,
# #                         value=o.value,
# #                         severity=o.severity.value,
# #                         news2_score=o.news2_score,
# #                         seriousness_points=o.seriousness_points,
# #                         next_node_key=o.next_node_key,
# #                     )
# #                     for o in n.options
# #                 ],
# #             )
# #             for n in flow.nodes
# #         ],
# #     )


# # # ============================================================
# # # ROUTES - UPDATE
# # # ============================================================
# # @router.put("/{flow_id}", response_model=dict)
# # def update_flow(
# #     flow_id: int,
# #     data: FlowUpdateIn,
# #     request: Request,
# #     db: Session = Depends(get_db),
# #     current_user: User = Depends(require_admin),
# # ):
# #     flow = (
# #         db.query(QuestionnaireFlow)
# #         .filter(
# #             QuestionnaireFlow.id == flow_id,
# #             QuestionnaireFlow.is_deleted == False,  # noqa: E712
# #         )
# #         .first()
# #     )

# #     if not flow:
# #         raise HTTPException(404, "Flow not found")

# #     # ✅ normalize nodes before saving
# #     normalized_nodes = normalize_nodes_for_type(data.nodes)

# #     # Delete old nodes
# #     db.query(FlowNode).filter(FlowNode.flow_id == flow.id).delete()

# #     # Update flow
# #     flow.name = data.name
# #     flow.description = data.description
# #     flow.flow_type = data.flow_type
# #     flow.status = data.status
# #     flow.start_node_key = data.start_node_key
# #     flow.version += 1
# #     flow.updated_at = datetime.utcnow()

# #     db.flush()

# #     # Create new nodes
# #     created_nodes = _create_nodes_from_data(flow.id, normalized_nodes, db)
# #     errors = validate_flow_integrity(flow, created_nodes)
# #     if errors:
# #         db.rollback()
# #         raise HTTPException(400, detail={"errors": errors})

# #     db.commit()
# #     db.refresh(flow)

# #     write_audit_log(
# #         db,
# #         "FLOW_UPDATED",
# #         user_id=current_user.id,
# #         request=request,
# #         details=f"flow_id={flow.id}, version={flow.version}",
# #     )
# #     return {"flow_id": flow.id, "version": flow.version, "message": "Flow updated successfully"}


# # # ============================================================
# # # ROUTES - DELETE
# # # ============================================================
# # @router.delete("/{flow_id}", response_model=dict)
# # def delete_flow(
# #     flow_id: int,
# #     request: Request,
# #     db: Session = Depends(get_db),
# #     current_user: User = Depends(require_admin),
# # ):
# #     flow = (
# #         db.query(QuestionnaireFlow)
# #         .filter(
# #             QuestionnaireFlow.id == flow_id,
# #             QuestionnaireFlow.is_deleted == False,  # noqa: E712
# #         )
# #         .first()
# #     )

# #     if not flow:
# #         raise HTTPException(404, "Flow not found")

# #     flow.is_deleted = True
# #     db.commit()

# #     write_audit_log(db, "FLOW_DELETED", user_id=current_user.id, request=request, details=f"flow_id={flow.id}")
# #     return {"message": "Flow deleted successfully"}


# # # ============================================================
# # # ROUTES - DEMO SEED
# # # ============================================================
# # @router.post("/demo/seed", response_model=dict)
# # def create_demo_flow(
# #     request: Request,
# #     db: Session = Depends(get_db),
# #     current_user: User = Depends(require_admin),
# # ):
# #     demo_data = FlowCreateIn(
# #         name="Virtual Ward Daily Check-in Demo",
# #         description="Daily health monitoring questionnaire with conditional paths",
# #         flow_type="DAILY_CHECKIN",
# #         status=FlowStatus.ACTIVE,
# #         start_node_key="1",
# #         nodes=[
# #             FlowNodeIn(
# #                 node_key="1",
# #                 node_type=FlowNodeType.QUESTION,
# #                 title="Temperature Check",
# #                 body_text="What is your temperature today?",
# #                 help_text="Use a thermometer and record in Celsius",
# #                 parent_node_key=None,
# #                 default_next_node_key="2",
# #                 options=[
# #                     FlowOptionIn(display_order=1, label="< 37.8°C (Normal)", value="normal", severity=SeverityLevel.GREEN, news2_score=0, seriousness_points=0, next_node_key="2"),
# #                     FlowOptionIn(display_order=2, label="37.8-39°C (Mild)", value="mild", severity=SeverityLevel.AMBER, news2_score=1, seriousness_points=1, next_node_key="1.1"),
# #                     FlowOptionIn(display_order=3, label="> 39°C (High)", value="high", severity=SeverityLevel.RED, news2_score=2, seriousness_points=3, next_node_key="1.2"),
# #                 ],
# #             ),
# #             FlowNodeIn(
# #                 node_key="1.1",
# #                 node_type=FlowNodeType.ALERT,
# #                 title="Mild Fever Alert",
# #                 body_text="You have a mild fever. Monitor your temperature and stay hydrated.",
# #                 auto_next_node_key="2",
# #                 alert_severity=SeverityLevel.AMBER,
# #                 notify_admin=False,
# #                 options=[],
# #             ),
# #             FlowNodeIn(
# #                 node_key="1.2",
# #                 node_type=FlowNodeType.ALERT,
# #                 title="High Fever Alert",
# #                 body_text="⚠️ High fever detected. Please contact your healthcare provider immediately.",
# #                 auto_next_node_key="END",
# #                 alert_severity=SeverityLevel.RED,
# #                 notify_admin=True,
# #                 options=[],
# #             ),
# #             FlowNodeIn(
# #                 node_key="2",
# #                 node_type=FlowNodeType.QUESTION,
# #                 title="Breathing Check",
# #                 body_text="How is your breathing today?",
# #                 help_text="Rate your breathing difficulty",
# #                 parent_node_key="1",
# #                 default_next_node_key="END",
# #                 options=[
# #                     FlowOptionIn(display_order=1, label="Normal", value="normal", severity=SeverityLevel.GREEN, news2_score=0, seriousness_points=0, next_node_key="END"),
# #                     FlowOptionIn(display_order=2, label="Slightly difficult", value="mild", severity=SeverityLevel.AMBER, news2_score=1, seriousness_points=1, next_node_key="END"),
# #                     FlowOptionIn(display_order=3, label="Very difficult", value="severe", severity=SeverityLevel.RED, news2_score=3, seriousness_points=3, next_node_key="2.1"),
# #                 ],
# #             ),
# #             FlowNodeIn(
# #                 node_key="2.1",
# #                 node_type=FlowNodeType.ALERT,
# #                 title="Breathing Difficulty Alert",
# #                 body_text="⚠️ Severe breathing difficulty detected. Seek immediate medical attention!",
# #                 auto_next_node_key="END",
# #                 alert_severity=SeverityLevel.RED,
# #                 notify_admin=True,
# #                 options=[],
# #             ),
# #         ],
# #     )

# #     # ✅ normalize (keeps demo safe too)
# #     normalized_nodes = normalize_nodes_for_type(demo_data.nodes)

# #     flow = QuestionnaireFlow(
# #         name=demo_data.name,
# #         description=demo_data.description,
# #         flow_type=demo_data.flow_type,
# #         status=demo_data.status,
# #         start_node_key=demo_data.start_node_key,
# #         version=1,
# #         created_by_user_id=current_user.id,
# #     )
# #     db.add(flow)
# #     db.flush()

# #     created_nodes = _create_nodes_from_data(flow.id, normalized_nodes, db)
# #     errors = validate_flow_integrity(flow, created_nodes)
# #     if errors:
# #         db.rollback()
# #         raise HTTPException(400, detail={"errors": errors})

# #     db.commit()
# #     db.refresh(flow)

# #     write_audit_log(db, "DEMO_FLOW_CREATED", user_id=current_user.id, request=request, details=f"flow_id={flow.id}")
# #     return {"flow_id": flow.id, "message": "Demo flow created successfully"}


# # # ============================================================
# # # ROUTES - VALIDATE
# # # ============================================================
# # @router.get("/{flow_id}/validate", response_model=dict)
# # def validate_flow(
# #     flow_id: int,
# #     db: Session = Depends(get_db),
# #     current_user: User = Depends(require_admin),
# # ):
# #     flow = (
# #         db.query(QuestionnaireFlow)
# #         .options(joinedload(QuestionnaireFlow.nodes).joinedload(FlowNode.options))
# #         .filter(
# #             QuestionnaireFlow.id == flow_id,
# #             QuestionnaireFlow.is_deleted == False,  # noqa: E712
# #         )
# #         .first()
# #     )

# #     if not flow:
# #         raise HTTPException(404, "Flow not found")

# #     errors = validate_flow_integrity(flow, flow.nodes)
# #     return {"flow_id": flow.id, "valid": len(errors) == 0, "errors": errors}

# # flows.py
# from __future__ import annotations

# from datetime import datetime
# from enum import Enum
# from typing import Optional, List, Dict, Set

# from fastapi import APIRouter, Depends, HTTPException, Request
# from pydantic import BaseModel, Field
# from sqlalchemy import (
#     Column,
#     Integer,
#     String,
#     Text,
#     DateTime,
#     ForeignKey,
#     Boolean,
#     Index,
#     UniqueConstraint,
#     Enum as SAEnum,
# )
# from sqlalchemy.orm import Session, relationship, joinedload

# from db import Base
# from auth import get_db, require_admin, write_audit_log
# from user import User

# router = APIRouter(prefix="/flows", tags=["Flows"])


# # ============================================================
# # ENUMS
# # ============================================================
# class FlowStatus(str, Enum):
#     DRAFT = "DRAFT"
#     ACTIVE = "ACTIVE"
#     ARCHIVED = "ARCHIVED"


# class FlowNodeType(str, Enum):
#     QUESTION = "QUESTION"
#     MESSAGE = "MESSAGE"
#     ALERT = "ALERT"


# class SeverityLevel(str, Enum):
#     GREEN = "GREEN"
#     AMBER = "AMBER"
#     RED = "RED"


# # ============================================================
# # SQLALCHEMY MODELS
# # ============================================================
# class QuestionnaireFlow(Base):
#     __tablename__ = "questionnaire_flows"

#     id = Column(Integer, primary_key=True)
#     name = Column(String(200), nullable=False, index=True)
#     description = Column(Text, nullable=True)
#     flow_type = Column(String(50), nullable=False, index=True)
#     status = Column(SAEnum(FlowStatus), nullable=False, default=FlowStatus.DRAFT, index=True)

#     start_node_key = Column(String(50), nullable=False)

#     version = Column(Integer, default=1, nullable=False)
#     parent_flow_id = Column(Integer, ForeignKey("questionnaire_flows.id"), nullable=True)

#     is_deleted = Column(Boolean, default=False, nullable=False, index=True)

#     created_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
#     created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
#     updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

#     created_by = relationship("User", foreign_keys=[created_by_user_id])
#     parent_flow = relationship("QuestionnaireFlow", remote_side=[id], foreign_keys=[parent_flow_id])

#     nodes = relationship(
#         "FlowNode",
#         back_populates="flow",
#         cascade="all, delete-orphan",
#         order_by="FlowNode.display_order",
#     )


# class FlowNode(Base):
#     __tablename__ = "flow_nodes"
#     __table_args__ = (
#         UniqueConstraint("flow_id", "node_key", name="uq_flow_node_key"),
#         Index("idx_flow_node_flow", "flow_id"),
#         Index("idx_flow_node_key", "node_key"),
#         Index("idx_flow_node_type", "node_type"),
#     )

#     id = Column(Integer, primary_key=True)
#     flow_id = Column(Integer, ForeignKey("questionnaire_flows.id", ondelete="CASCADE"), nullable=False)

#     node_key = Column(String(50), nullable=False)
#     node_type = Column(SAEnum(FlowNodeType), nullable=False)

#     title = Column(String(200), nullable=True)
#     body_text = Column(Text, nullable=False)
#     help_text = Column(Text, nullable=True)

#     parent_node_key = Column(String(50), nullable=True)

#     depth_level = Column(Integer, default=0, nullable=False)
#     display_order = Column(Integer, default=0, nullable=False)

#     default_next_node_key = Column(String(50), nullable=True)
#     auto_next_node_key = Column(String(50), nullable=True)

#     ui_ack_required = Column(Boolean, default=False, nullable=False)

#     alert_severity = Column(SAEnum(SeverityLevel), nullable=True)
#     notify_admin = Column(Boolean, default=False, nullable=False)

#     flow = relationship("QuestionnaireFlow", back_populates="nodes")
#     options = relationship(
#         "FlowNodeOption",
#         back_populates="node",
#         cascade="all, delete-orphan",
#         order_by="FlowNodeOption.display_order",
#     )


# class FlowNodeOption(Base):
#     __tablename__ = "flow_node_options"

#     id = Column(Integer, primary_key=True)
#     node_id = Column(Integer, ForeignKey("flow_nodes.id", ondelete="CASCADE"), nullable=False, index=True)

#     display_order = Column(Integer, default=0, nullable=False)
#     label = Column(String(200), nullable=False)
#     value = Column(String(200), nullable=False)

#     severity = Column(SAEnum(SeverityLevel), default=SeverityLevel.GREEN, nullable=False)
#     news2_score = Column(Integer, default=0, nullable=False)
#     seriousness_points = Column(Integer, default=0, nullable=False)

#     next_node_key = Column(String(50), nullable=True)

#     node = relationship("FlowNode", back_populates="options")


# # ============================================================
# # PYDANTIC SCHEMAS
# # ============================================================
# class FlowOptionIn(BaseModel):
#     display_order: int
#     label: str
#     value: str
#     severity: SeverityLevel
#     news2_score: int = 0
#     seriousness_points: int = 0
#     next_node_key: Optional[str] = None


# class FlowNodeIn(BaseModel):
#     node_key: str
#     node_type: FlowNodeType
#     title: Optional[str] = None
#     body_text: str
#     help_text: Optional[str] = None
#     parent_node_key: Optional[str] = None
#     default_next_node_key: Optional[str] = None
#     auto_next_node_key: Optional[str] = None
#     ui_ack_required: bool = False
#     alert_severity: Optional[SeverityLevel] = None
#     notify_admin: bool = False
#     options: List[FlowOptionIn] = Field(default_factory=list)


# class FlowCreateIn(BaseModel):
#     name: str = Field(min_length=1, max_length=200)
#     description: Optional[str] = None
#     flow_type: str = Field(min_length=1, max_length=50)
#     status: FlowStatus = FlowStatus.DRAFT
#     start_node_key: str
#     nodes: List[FlowNodeIn] = Field(min_items=1)


# class FlowUpdateIn(BaseModel):
#     name: str = Field(min_length=1, max_length=200)
#     description: Optional[str] = None
#     flow_type: str = Field(min_length=1, max_length=50)
#     status: FlowStatus
#     start_node_key: str
#     nodes: List[FlowNodeIn] = Field(min_items=1)


# class FlowOptionOut(BaseModel):
#     id: int
#     display_order: int
#     label: str
#     value: str
#     severity: str
#     news2_score: int
#     seriousness_points: int
#     next_node_key: Optional[str]

#     class Config:
#         from_attributes = True


# class FlowNodeOut(BaseModel):
#     id: int
#     node_key: str
#     node_type: str
#     title: Optional[str]
#     body_text: str
#     help_text: Optional[str]
#     parent_node_key: Optional[str]
#     depth_level: int
#     default_next_node_key: Optional[str]
#     auto_next_node_key: Optional[str]
#     ui_ack_required: bool
#     alert_severity: Optional[str]
#     notify_admin: bool
#     options: List[FlowOptionOut]

#     class Config:
#         from_attributes = True


# class FlowDetailOut(BaseModel):
#     id: int
#     name: str
#     description: Optional[str]
#     flow_type: str
#     status: str
#     start_node_key: str
#     version: int
#     created_at: datetime
#     updated_at: datetime
#     created_by: dict
#     nodes: List[FlowNodeOut]

#     class Config:
#         from_attributes = True


# class FlowOut(BaseModel):
#     id: int
#     name: str
#     description: Optional[str]
#     flow_type: str
#     status: str
#     start_node_key: str
#     version: int
#     node_count: int
#     created_at: datetime
#     created_by: dict

#     class Config:
#         from_attributes = True


# class FlowListOut(BaseModel):
#     total: int
#     items: List[FlowOut]


# # ============================================================
# # NORMALIZE INPUT
# # ============================================================
# def normalize_nodes_for_type(nodes: List[FlowNodeIn]) -> List[FlowNodeIn]:
#     """
#     MESSAGE/ALERT safe defaults:
#     - force options=[]
#     - clear default_next_node_key
#     - ensure auto_next_node_key (default END)
#     - ALERT default severity RED
#     """
#     normalized: List[FlowNodeIn] = []

#     for n in nodes:
#         if n.node_type in (FlowNodeType.MESSAGE, FlowNodeType.ALERT):
#             normalized.append(
#                 FlowNodeIn(
#                     node_key=n.node_key,
#                     node_type=n.node_type,
#                     title=n.title,
#                     body_text=n.body_text,
#                     help_text=n.help_text,
#                     parent_node_key=n.parent_node_key,
#                     default_next_node_key=None,
#                     auto_next_node_key=n.auto_next_node_key or "END",
#                     ui_ack_required=n.ui_ack_required,
#                     alert_severity=(n.alert_severity or SeverityLevel.RED) if n.node_type == FlowNodeType.ALERT else None,
#                     notify_admin=bool(n.notify_admin) if n.node_type == FlowNodeType.ALERT else False,
#                     options=[],
#                 )
#             )
#         else:
#             normalized.append(n)

#     return normalized


# # ============================================================
# # VALIDATION
# # ============================================================
# def validate_flow_integrity(flow: QuestionnaireFlow, nodes: List[FlowNode]) -> List[str]:
#     errors: List[str] = []
#     if not nodes:
#         return ["Flow must have at least one node"]

#     node_keys = {n.node_key for n in nodes}
#     if flow.start_node_key not in node_keys:
#         errors.append(f"start_node_key '{flow.start_node_key}' not found")

#     for node in nodes:
#         if node.node_type == FlowNodeType.QUESTION:
#             if not node.options or len(node.options) < 2:
#                 errors.append(f"Node '{node.node_key}': QUESTION must have >= 2 options")

#             if node.default_next_node_key and node.default_next_node_key != "END" and node.default_next_node_key not in node_keys:
#                 errors.append(f"Node '{node.node_key}': invalid default_next_node_key")

#             for opt in node.options:
#                 if opt.next_node_key and opt.next_node_key != "END" and opt.next_node_key not in node_keys:
#                     errors.append(f"Node '{node.node_key}', option '{opt.label}': invalid next_node_key")

#         elif node.node_type in (FlowNodeType.MESSAGE, FlowNodeType.ALERT):
#             if not node.auto_next_node_key:
#                 errors.append(f"Node '{node.node_key}': {node.node_type.value} must have auto_next_node_key")
#             elif node.auto_next_node_key != "END" and node.auto_next_node_key not in node_keys:
#                 errors.append(f"Node '{node.node_key}': invalid auto_next_node_key")

#             if node.options and len(node.options) > 0:
#                 errors.append(f"Node '{node.node_key}': {node.node_type.value} must not have options")

#             if node.node_type == FlowNodeType.ALERT and not node.alert_severity:
#                 errors.append(f"Node '{node.node_key}': ALERT must have alert_severity")

#     # Standard DFS cycle detection
#     graph: Dict[str, List[str]] = {}

#     def add_edge(src: str, dst: Optional[str]):
#         if not dst:
#             return
#         graph.setdefault(src, [])
#         graph[src].append(dst)

#     for n in nodes:
#         if n.node_type == FlowNodeType.QUESTION:
#             add_edge(n.node_key, n.default_next_node_key)
#             for o in n.options:
#                 add_edge(n.node_key, o.next_node_key)
#         else:
#             add_edge(n.node_key, n.auto_next_node_key)

#     visited: Set[str] = set()
#     stack: Set[str] = set()

#     def dfs(u: str) -> bool:
#         if u == "END":
#             return False
#         if u in stack:
#             return True
#         if u in visited:
#             return False
#         visited.add(u)
#         stack.add(u)
#         for v in graph.get(u, []):
#             if dfs(v):
#                 return True
#         stack.remove(u)
#         return False

#     if flow.start_node_key in node_keys and dfs(flow.start_node_key):
#         errors.append("Flow contains cycles")

#     return errors


# # ============================================================
# # HELPER
# # ============================================================
# def _create_nodes_from_data(flow_id: int, nodes_data: List[FlowNodeIn], db: Session) -> List[FlowNode]:
#     created_nodes: List[FlowNode] = []

#     for idx, node_data in enumerate(nodes_data):
#         node = FlowNode(
#             flow_id=flow_id,
#             node_key=node_data.node_key,
#             node_type=node_data.node_type,
#             title=node_data.title,
#             body_text=node_data.body_text,
#             help_text=node_data.help_text,
#             parent_node_key=node_data.parent_node_key,
#             depth_level=node_data.node_key.count("."),
#             display_order=idx,
#             default_next_node_key=node_data.default_next_node_key,
#             auto_next_node_key=node_data.auto_next_node_key,
#             ui_ack_required=node_data.ui_ack_required,
#             alert_severity=node_data.alert_severity,
#             notify_admin=node_data.notify_admin,
#         )

#         for opt_data in (node_data.options or []):
#             node.options.append(
#                 FlowNodeOption(
#                     display_order=opt_data.display_order,
#                     label=opt_data.label,
#                     value=opt_data.value,
#                     severity=opt_data.severity,
#                     news2_score=opt_data.news2_score,
#                     seriousness_points=opt_data.seriousness_points,
#                     next_node_key=opt_data.next_node_key,
#                 )
#             )

#         db.add(node)
#         created_nodes.append(node)

#     db.flush()
#     return created_nodes


# def _safe_user_name(u: Optional[User]) -> str:
#     if not u:
#         return ""
#     return (getattr(u, "name", None) or getattr(u, "full_name", None) or "").strip()


# # ============================================================
# # ROUTES - CREATE
# # ============================================================
# @router.post("/", response_model=dict)
# def create_flow(
#     data: FlowCreateIn,
#     request: Request,
#     db: Session = Depends(get_db),
#     current_user: User = Depends(require_admin),
# ):
#     normalized_nodes = normalize_nodes_for_type(data.nodes)

#     flow = QuestionnaireFlow(
#         name=data.name,
#         description=data.description,
#         flow_type=data.flow_type,
#         status=data.status,
#         start_node_key=data.start_node_key,
#         version=1,
#         created_by_user_id=current_user.id,
#     )
#     db.add(flow)
#     db.flush()

#     created_nodes = _create_nodes_from_data(flow.id, normalized_nodes, db)
#     errors = validate_flow_integrity(flow, created_nodes)
#     if errors:
#         db.rollback()
#         raise HTTPException(400, detail={"errors": errors})

#     db.commit()
#     db.refresh(flow)

#     write_audit_log(db, "FLOW_CREATED", user_id=current_user.id, request=request, details=f"flow_id={flow.id}")
#     return {"flow_id": flow.id, "message": "Flow created successfully"}


# # ============================================================
# # ROUTES - LIST
# # ============================================================
# @router.get("/", response_model=FlowListOut)
# def list_flows(
#     db: Session = Depends(get_db),
#     current_user: User = Depends(require_admin),
#     q: Optional[str] = None,
#     flow_type: Optional[str] = None,
#     status: Optional[FlowStatus] = None,
#     skip: int = 0,
#     limit: int = 20,
# ):
#     query = (
#         db.query(QuestionnaireFlow)
#         .options(joinedload(QuestionnaireFlow.created_by))
#         .filter(QuestionnaireFlow.is_deleted == False)  # noqa: E712
#     )

#     if q:
#         query = query.filter(QuestionnaireFlow.name.ilike(f"%{q.strip()}%"))
#     if flow_type:
#         query = query.filter(QuestionnaireFlow.flow_type == flow_type)
#     if status:
#         query = query.filter(QuestionnaireFlow.status == status)

#     total = query.count()
#     flows = (
#         query.order_by(QuestionnaireFlow.created_at.desc())
#         .offset(skip)
#         .limit(min(limit, 100))
#         .all()
#     )

#     items: List[FlowOut] = []
#     for f in flows:
#         items.append(
#             FlowOut(
#                 id=f.id,
#                 name=f.name,
#                 description=f.description,
#                 flow_type=f.flow_type,
#                 status=f.status.value,
#                 start_node_key=f.start_node_key,
#                 version=f.version,
#                 node_count=db.query(FlowNode).filter(FlowNode.flow_id == f.id).count(),
#                 created_at=f.created_at,
#                 created_by={
#                     "id": f.created_by.id if f.created_by else None,
#                     "name": _safe_user_name(f.created_by),
#                     "email": getattr(f.created_by, "email", "") if f.created_by else "",
#                 },
#             )
#         )

#     return FlowListOut(total=total, items=items)


# # ============================================================
# # ROUTES - GET DETAIL
# # ============================================================
# @router.get("/{flow_id}", response_model=FlowDetailOut)
# def get_flow(
#     flow_id: int,
#     db: Session = Depends(get_db),
#     current_user: User = Depends(require_admin),
# ):
#     flow = (
#         db.query(QuestionnaireFlow)
#         .options(
#             joinedload(QuestionnaireFlow.created_by),
#             joinedload(QuestionnaireFlow.nodes).joinedload(FlowNode.options),
#         )
#         .filter(
#             QuestionnaireFlow.id == flow_id,
#             QuestionnaireFlow.is_deleted == False,  # noqa: E712
#         )
#         .first()
#     )

#     if not flow:
#         raise HTTPException(404, "Flow not found")

#     return FlowDetailOut(
#         id=flow.id,
#         name=flow.name,
#         description=flow.description,
#         flow_type=flow.flow_type,
#         status=flow.status.value,
#         start_node_key=flow.start_node_key,
#         version=flow.version,
#         created_at=flow.created_at,
#         updated_at=flow.updated_at,
#         created_by={
#             "id": flow.created_by.id if flow.created_by else None,
#             "name": _safe_user_name(flow.created_by),
#             "email": getattr(flow.created_by, "email", "") if flow.created_by else "",
#         },
#         nodes=[
#             FlowNodeOut(
#                 id=n.id,
#                 node_key=n.node_key,
#                 node_type=n.node_type.value,
#                 title=n.title,
#                 body_text=n.body_text,
#                 help_text=n.help_text,
#                 parent_node_key=n.parent_node_key,
#                 depth_level=n.depth_level,
#                 default_next_node_key=n.default_next_node_key,
#                 auto_next_node_key=n.auto_next_node_key,
#                 ui_ack_required=n.ui_ack_required,
#                 alert_severity=n.alert_severity.value if n.alert_severity else None,
#                 notify_admin=n.notify_admin,
#                 options=[
#                     FlowOptionOut(
#                         id=o.id,
#                         display_order=o.display_order,
#                         label=o.label,
#                         value=o.value,
#                         severity=o.severity.value,
#                         news2_score=o.news2_score,
#                         seriousness_points=o.seriousness_points,
#                         next_node_key=o.next_node_key,
#                     )
#                     for o in n.options
#                 ],
#             )
#             for n in flow.nodes
#         ],
#     )


# # ============================================================
# # ROUTES - UPDATE
# # ============================================================
# @router.put("/{flow_id}", response_model=dict)
# def update_flow(
#     flow_id: int,
#     data: FlowUpdateIn,
#     request: Request,
#     db: Session = Depends(get_db),
#     current_user: User = Depends(require_admin),
# ):
#     flow = (
#         db.query(QuestionnaireFlow)
#         .options(joinedload(QuestionnaireFlow.nodes).joinedload(FlowNode.options))
#         .filter(
#             QuestionnaireFlow.id == flow_id,
#             QuestionnaireFlow.is_deleted == False,  # noqa: E712
#         )
#         .first()
#     )

#     if not flow:
#         raise HTTPException(404, "Flow not found")

#     normalized_nodes = normalize_nodes_for_type(data.nodes)

#     # ✅ ORM-safe delete (cascades options too)
#     flow.nodes.clear()
#     db.flush()

#     flow.name = data.name
#     flow.description = data.description
#     flow.flow_type = data.flow_type
#     flow.status = data.status
#     flow.start_node_key = data.start_node_key
#     flow.version += 1
#     flow.updated_at = datetime.utcnow()

#     db.flush()

#     created_nodes = _create_nodes_from_data(flow.id, normalized_nodes, db)
#     errors = validate_flow_integrity(flow, created_nodes)
#     if errors:
#         db.rollback()
#         raise HTTPException(400, detail={"errors": errors})

#     db.commit()
#     db.refresh(flow)

#     write_audit_log(
#         db,
#         "FLOW_UPDATED",
#         user_id=current_user.id,
#         request=request,
#         details=f"flow_id={flow.id}, version={flow.version}",
#     )
#     return {"flow_id": flow.id, "version": flow.version, "message": "Flow updated successfully"}


# # ============================================================
# # ROUTES - DELETE
# # ============================================================
# @router.delete("/{flow_id}", response_model=dict)
# def delete_flow(
#     flow_id: int,
#     request: Request,
#     db: Session = Depends(get_db),
#     current_user: User = Depends(require_admin),
# ):
#     flow = (
#         db.query(QuestionnaireFlow)
#         .filter(
#             QuestionnaireFlow.id == flow_id,
#             QuestionnaireFlow.is_deleted == False,  # noqa: E712
#         )
#         .first()
#     )

#     if not flow:
#         raise HTTPException(404, "Flow not found")

#     flow.is_deleted = True
#     db.commit()

#     write_audit_log(db, "FLOW_DELETED", user_id=current_user.id, request=request, details=f"flow_id={flow.id}")
#     return {"message": "Flow deleted successfully"}


# # ============================================================
# # ROUTES - VALIDATE
# # ============================================================
# @router.get("/{flow_id}/validate", response_model=dict)
# def validate_flow(
#     flow_id: int,
#     db: Session = Depends(get_db),
#     current_user: User = Depends(require_admin),
# ):
#     flow = (
#         db.query(QuestionnaireFlow)
#         .options(joinedload(QuestionnaireFlow.nodes).joinedload(FlowNode.options))
#         .filter(
#             QuestionnaireFlow.id == flow_id,
#             QuestionnaireFlow.is_deleted == False,  # noqa: E712
#         )
#         .first()
#     )

#     if not flow:
#         raise HTTPException(404, "Flow not found")

#     errors = validate_flow_integrity(flow, flow.nodes)
#     return {"flow_id": flow.id, "valid": len(errors) == 0, "errors": errors}


# flows.py
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Set

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    DateTime,
    ForeignKey,
    Boolean,
    Index,
    UniqueConstraint,
    Enum as SAEnum,
)
from sqlalchemy.orm import Session, relationship, joinedload
from pathlib import Path
from excel_seed import build_nodes_from_excel


from db import Base
from auth import get_db, require_admin, write_audit_log
from user import User

router = APIRouter(prefix="/flows", tags=["Flows"])

@router.post("/{flow_id}/seed-demo-from-excel", response_model=dict)
def seed_demo_from_excel(
    flow_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    # 1) find flow
    flow = (
        db.query(QuestionnaireFlow)
        .options(joinedload(QuestionnaireFlow.nodes).joinedload(FlowNode.options))
        .filter(
            QuestionnaireFlow.id == flow_id,
            QuestionnaireFlow.is_deleted == False,  # noqa: E712
        )
        .first()
    )
    if not flow:
        raise HTTPException(404, "Flow not found")

    # 2) load excel fixture (put file here)
    excel_path = Path(__file__).resolve().parent / "fixtures" / "scoring system4.xlsx"
    if not excel_path.exists():
        raise HTTPException(500, f"Excel fixture not found: {excel_path}")

    # 3) build nodes
    start_node_key, nodes = build_nodes_from_excel(excel_path)

    # 4) overwrite ONLY this flow's nodes (same pattern as update_flow)
    try:
        # clear old nodes/options for THIS flow only
        flow.nodes.clear()
        db.flush()

        flow.start_node_key = start_node_key
        flow.version += 1
        flow.updated_at = datetime.utcnow()

        # recreate
        created_nodes = _create_nodes_from_data(flow.id, nodes, db)

        # validate using your existing validator
        errors = validate_flow_integrity(flow, created_nodes)
        if errors:
            db.rollback()
            raise HTTPException(400, detail={"errors": errors})

        db.commit()
        db.refresh(flow)

        write_audit_log(
            db,
            "FLOW_DEMO_SEEDED_FROM_EXCEL",
            user_id=current_user.id,
            request=request,
            details=f"flow_id={flow.id}, version={flow.version}",
        )

        return {
            "flow_id": flow.id,
            "version": flow.version,
            "node_count": len(created_nodes),
            "message": "Demo questions seeded from Excel successfully",
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(500, detail=f"Seeding failed: {str(e)}")


# ============================================================
# ENUMS
# ============================================================
class FlowStatus(str, Enum):
    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    ARCHIVED = "ARCHIVED"


class FlowNodeType(str, Enum):
    QUESTION = "QUESTION"
    MESSAGE = "MESSAGE"
    ALERT = "ALERT"


class SeverityLevel(str, Enum):
    GREEN = "GREEN"
    AMBER = "AMBER"
    RED = "RED"


# ============================================================
# CATEGORY CONSTANTS (fixed: only 2)
# ============================================================
CATEGORY_CLINICAL_OBS_COLORECTAL = 1
CATEGORY_SYMPTOMS_AND_SIGNS = 2
ALLOWED_CATEGORIES = {CATEGORY_CLINICAL_OBS_COLORECTAL, CATEGORY_SYMPTOMS_AND_SIGNS}


# ============================================================
# SQLALCHEMY MODELS
# ============================================================
class QuestionnaireFlow(Base):
    __tablename__ = "questionnaire_flows"

    id = Column(Integer, primary_key=True)
    name = Column(String(200), nullable=False, index=True)
    description = Column(Text, nullable=True)
    flow_type = Column(String(50), nullable=False, index=True)
    status = Column(SAEnum(FlowStatus), nullable=False, default=FlowStatus.DRAFT, index=True)

    start_node_key = Column(String(50), nullable=False)

    version = Column(Integer, default=1, nullable=False)
    parent_flow_id = Column(Integer, ForeignKey("questionnaire_flows.id"), nullable=True)

    is_deleted = Column(Boolean, default=False, nullable=False, index=True)

    created_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    created_by = relationship("User", foreign_keys=[created_by_user_id])
    parent_flow = relationship("QuestionnaireFlow", remote_side=[id], foreign_keys=[parent_flow_id])

    nodes = relationship(
        "FlowNode",
        back_populates="flow",
        cascade="all, delete-orphan",
        order_by="FlowNode.display_order",
    )


class FlowNode(Base):
    __tablename__ = "flow_nodes"
    __table_args__ = (
        UniqueConstraint("flow_id", "node_key", name="uq_flow_node_key"),
        Index("idx_flow_node_flow", "flow_id"),
        Index("idx_flow_node_key", "node_key"),
        Index("idx_flow_node_type", "node_type"),
        Index("idx_flow_node_category", "category"),
    )

    id = Column(Integer, primary_key=True)
    flow_id = Column(Integer, ForeignKey("questionnaire_flows.id", ondelete="CASCADE"), nullable=False)

    node_key = Column(String(50), nullable=False)
    node_type = Column(SAEnum(FlowNodeType), nullable=False)

    # ✅ Category grouping layer (fixed: 1 or 2). DB migration already added this column.
    category = Column(Integer, nullable=False, default=CATEGORY_CLINICAL_OBS_COLORECTAL)

    title = Column(String(200), nullable=True)
    body_text = Column(Text, nullable=False)
    help_text = Column(Text, nullable=True)

    parent_node_key = Column(String(50), nullable=True)

    depth_level = Column(Integer, default=0, nullable=False)
    display_order = Column(Integer, default=0, nullable=False)

    default_next_node_key = Column(String(50), nullable=True)
    auto_next_node_key = Column(String(50), nullable=True)

    ui_ack_required = Column(Boolean, default=False, nullable=False)

    alert_severity = Column(SAEnum(SeverityLevel), nullable=True)
    notify_admin = Column(Boolean, default=False, nullable=False)

    flow = relationship("QuestionnaireFlow", back_populates="nodes")
    options = relationship(
        "FlowNodeOption",
        back_populates="node",
        cascade="all, delete-orphan",
        order_by="FlowNodeOption.display_order",
    )


class FlowNodeOption(Base):
    __tablename__ = "flow_node_options"

    id = Column(Integer, primary_key=True)
    node_id = Column(Integer, ForeignKey("flow_nodes.id", ondelete="CASCADE"), nullable=False, index=True)

    display_order = Column(Integer, default=0, nullable=False)
    label = Column(String(200), nullable=False)
    value = Column(String(200), nullable=False)

    severity = Column(SAEnum(SeverityLevel), default=SeverityLevel.GREEN, nullable=False)
    news2_score = Column(Integer, default=0, nullable=False)
    seriousness_points = Column(Integer, default=0, nullable=False)

    next_node_key = Column(String(50), nullable=True)

    node = relationship("FlowNode", back_populates="options")


# ============================================================
# PYDANTIC SCHEMAS
# ============================================================
class FlowOptionIn(BaseModel):
    display_order: int
    label: str
    value: str
    severity: SeverityLevel
    news2_score: int = 0
    seriousness_points: int = 0
    next_node_key: Optional[str] = None


class FlowNodeIn(BaseModel):
    node_key: str
    node_type: FlowNodeType

    # ✅ Category included in payload. Default = 1 for backwards compatibility.
    category: int = Field(default=CATEGORY_CLINICAL_OBS_COLORECTAL)

    title: Optional[str] = None
    body_text: str
    help_text: Optional[str] = None
    parent_node_key: Optional[str] = None
    default_next_node_key: Optional[str] = None
    auto_next_node_key: Optional[str] = None
    ui_ack_required: bool = False
    alert_severity: Optional[SeverityLevel] = None
    notify_admin: bool = False
    options: List[FlowOptionIn] = Field(default_factory=list)


class FlowCreateIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: Optional[str] = None
    flow_type: str = Field(min_length=1, max_length=50)
    status: FlowStatus = FlowStatus.DRAFT
    start_node_key: str
    nodes: List[FlowNodeIn] = Field(min_items=1)


class FlowUpdateIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: Optional[str] = None
    flow_type: str = Field(min_length=1, max_length=50)
    status: FlowStatus
    start_node_key: str
    nodes: List[FlowNodeIn] = Field(min_items=1)


class FlowOptionOut(BaseModel):
    id: int
    display_order: int
    label: str
    value: str
    severity: str
    news2_score: int
    seriousness_points: int
    next_node_key: Optional[str]

    class Config:
        from_attributes = True


class FlowNodeOut(BaseModel):
    id: int
    node_key: str
    node_type: str

    # ✅ Category returned
    category: int

    title: Optional[str]
    body_text: str
    help_text: Optional[str]
    parent_node_key: Optional[str]
    depth_level: int
    default_next_node_key: Optional[str]
    auto_next_node_key: Optional[str]
    ui_ack_required: bool
    alert_severity: Optional[str]
    notify_admin: bool
    options: List[FlowOptionOut]

    class Config:
        from_attributes = True


class FlowDetailOut(BaseModel):
    id: int
    name: str
    description: Optional[str]
    flow_type: str
    status: str
    start_node_key: str
    version: int
    created_at: datetime
    updated_at: datetime
    created_by: dict
    nodes: List[FlowNodeOut]

    class Config:
        from_attributes = True


class FlowOut(BaseModel):
    id: int
    name: str
    description: Optional[str]
    flow_type: str
    status: str
    start_node_key: str
    version: int
    node_count: int
    created_at: datetime
    created_by: dict

    class Config:
        from_attributes = True


class FlowListOut(BaseModel):
    total: int
    items: List[FlowOut]


# ============================================================
# NORMALIZE INPUT
# ============================================================
def normalize_nodes_for_type(nodes: List[FlowNodeIn]) -> List[FlowNodeIn]:
    """
    MESSAGE/ALERT safe defaults:
    - force options=[]
    - clear default_next_node_key
    - ensure auto_next_node_key (default END)
    - ALERT default severity RED
    """
    normalized: List[FlowNodeIn] = []

    for n in nodes:
        if n.node_type in (FlowNodeType.MESSAGE, FlowNodeType.ALERT):
            normalized.append(
                FlowNodeIn(
                    node_key=n.node_key,
                    node_type=n.node_type,
                    category=n.category,  # ✅ preserve category
                    title=n.title,
                    body_text=n.body_text,
                    help_text=n.help_text,
                    parent_node_key=n.parent_node_key,
                    default_next_node_key=None,
                    auto_next_node_key=n.auto_next_node_key or "END",
                    ui_ack_required=n.ui_ack_required,
                    alert_severity=(n.alert_severity or SeverityLevel.RED) if n.node_type == FlowNodeType.ALERT else None,
                    notify_admin=bool(n.notify_admin) if n.node_type == FlowNodeType.ALERT else False,
                    options=[],
                )
            )
        else:
            normalized.append(n)

    return normalized


# ============================================================
# VALIDATION
# ============================================================
def validate_flow_integrity(flow: QuestionnaireFlow, nodes: List[FlowNode]) -> List[str]:
    errors: List[str] = []
    if not nodes:
        return ["Flow must have at least one node"]

    node_by_key: Dict[str, FlowNode] = {n.node_key: n for n in nodes}
    node_keys = set(node_by_key.keys())

    if flow.start_node_key not in node_keys:
        errors.append(f"start_node_key '{flow.start_node_key}' not found")

    # ---------------- Category validation ----------------
    for n in nodes:
        if n.category not in ALLOWED_CATEGORIES:
            errors.append(f"Node '{n.node_key}': category must be 1 or 2")

    # Parent-child category match
    for n in nodes:
        if not n.parent_node_key:
            continue
        parent = node_by_key.get(n.parent_node_key)
        if not parent:
            # parent missing is not necessarily fatal for validation, but it's usually a modeling error
            errors.append(f"Node '{n.node_key}': parent_node_key '{n.parent_node_key}' not found")
            continue
        if n.category != parent.category:
            errors.append(
                f"Node '{n.node_key}': category ({n.category}) must match parent '{parent.node_key}' category ({parent.category})"
            )

    # Helper: check next-node category consistency
    def check_next_same_category(src_key: str, dst_key: Optional[str], relation: str):
        if not dst_key or dst_key == "END":
            return
        dst = node_by_key.get(dst_key)
        if not dst:
            return
        src = node_by_key.get(src_key)
        if not src:
            return
        if src.category != dst.category:
            errors.append(
                f"Node '{src_key}': {relation} '{dst_key}' must be in same category (src={src.category}, dst={dst.category})"
            )

    # ---------------- Existing node-type validation ----------------
    for node in nodes:
        if node.node_type == FlowNodeType.QUESTION:
            if not node.options or len(node.options) < 2:
                errors.append(f"Node '{node.node_key}': QUESTION must have >= 2 options")

            if node.default_next_node_key and node.default_next_node_key != "END" and node.default_next_node_key not in node_keys:
                errors.append(f"Node '{node.node_key}': invalid default_next_node_key")
            else:
                # ✅ enforce same-category next
                check_next_same_category(node.node_key, node.default_next_node_key, "default_next_node_key")

            for opt in node.options:
                if opt.next_node_key and opt.next_node_key != "END" and opt.next_node_key not in node_keys:
                    errors.append(f"Node '{node.node_key}', option '{opt.label}': invalid next_node_key")
                else:
                    # ✅ enforce same-category option next
                    check_next_same_category(node.node_key, opt.next_node_key, "option next_node_key")

        elif node.node_type in (FlowNodeType.MESSAGE, FlowNodeType.ALERT):
            if not node.auto_next_node_key:
                errors.append(f"Node '{node.node_key}': {node.node_type.value} must have auto_next_node_key")
            elif node.auto_next_node_key != "END" and node.auto_next_node_key not in node_keys:
                errors.append(f"Node '{node.node_key}': invalid auto_next_node_key")
            else:
                # ✅ enforce same-category next
                check_next_same_category(node.node_key, node.auto_next_node_key, "auto_next_node_key")

            if node.options and len(node.options) > 0:
                errors.append(f"Node '{node.node_key}': {node.node_type.value} must not have options")

            if node.node_type == FlowNodeType.ALERT and not node.alert_severity:
                errors.append(f"Node '{node.node_key}': ALERT must have alert_severity")

    # ---------------- Standard DFS cycle detection ----------------
    graph: Dict[str, List[str]] = {}

    def add_edge(src: str, dst: Optional[str]):
        if not dst:
            return
        graph.setdefault(src, [])
        graph[src].append(dst)

    for n in nodes:
        if n.node_type == FlowNodeType.QUESTION:
            add_edge(n.node_key, n.default_next_node_key)
            for o in n.options:
                add_edge(n.node_key, o.next_node_key)
        else:
            add_edge(n.node_key, n.auto_next_node_key)

    visited: Set[str] = set()
    stack: Set[str] = set()

    def dfs(u: str) -> bool:
        if u == "END":
            return False
        if u in stack:
            return True
        if u in visited:
            return False
        visited.add(u)
        stack.add(u)
        for v in graph.get(u, []):
            if dfs(v):
                return True
        stack.remove(u)
        return False

    if flow.start_node_key in node_keys and dfs(flow.start_node_key):
        errors.append("Flow contains cycles")

    return errors


# ============================================================
# HELPER
# ============================================================
def _create_nodes_from_data(flow_id: int, nodes_data: List[FlowNodeIn], db: Session) -> List[FlowNode]:
    created_nodes: List[FlowNode] = []

    for idx, node_data in enumerate(nodes_data):
        node = FlowNode(
            flow_id=flow_id,
            node_key=node_data.node_key,
            node_type=node_data.node_type,
            category=node_data.category or CATEGORY_CLINICAL_OBS_COLORECTAL,  # ✅ persist category (default=1)
            title=node_data.title,
            body_text=node_data.body_text,
            help_text=node_data.help_text,
            parent_node_key=node_data.parent_node_key,
            depth_level=node_data.node_key.count("."),
            display_order=idx,
            default_next_node_key=node_data.default_next_node_key,
            auto_next_node_key=node_data.auto_next_node_key,
            ui_ack_required=node_data.ui_ack_required,
            alert_severity=node_data.alert_severity,
            notify_admin=node_data.notify_admin,
        )

        for opt_data in (node_data.options or []):
            node.options.append(
                FlowNodeOption(
                    display_order=opt_data.display_order,
                    label=opt_data.label,
                    value=opt_data.value,
                    severity=opt_data.severity,
                    news2_score=opt_data.news2_score,
                    seriousness_points=opt_data.seriousness_points,
                    next_node_key=opt_data.next_node_key,
                )
            )

        db.add(node)
        created_nodes.append(node)

    db.flush()
    return created_nodes


def _safe_user_name(u: Optional[User]) -> str:
    if not u:
        return ""
    return (getattr(u, "name", None) or getattr(u, "full_name", None) or "").strip()


# ============================================================
# ROUTES - CREATE
# ============================================================
@router.post("/", response_model=dict)
def create_flow(
    data: FlowCreateIn,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    normalized_nodes = normalize_nodes_for_type(data.nodes)

    flow = QuestionnaireFlow(
        name=data.name,
        description=data.description,
        flow_type=data.flow_type,
        status=data.status,
        start_node_key=data.start_node_key,
        version=1,
        created_by_user_id=current_user.id,
    )
    db.add(flow)
    db.flush()

    created_nodes = _create_nodes_from_data(flow.id, normalized_nodes, db)
    errors = validate_flow_integrity(flow, created_nodes)
    if errors:
        db.rollback()
        raise HTTPException(400, detail={"errors": errors})

    db.commit()
    db.refresh(flow)

    write_audit_log(db, "FLOW_CREATED", user_id=current_user.id, request=request, details=f"flow_id={flow.id}")
    return {"flow_id": flow.id, "message": "Flow created successfully"}


# ============================================================
# ROUTES - LIST
# ============================================================
@router.get("/", response_model=FlowListOut)
def list_flows(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
    q: Optional[str] = None,
    flow_type: Optional[str] = None,
    status: Optional[FlowStatus] = None,
    skip: int = 0,
    limit: int = 20,
):
    query = (
        db.query(QuestionnaireFlow)
        .options(joinedload(QuestionnaireFlow.created_by))
        .filter(QuestionnaireFlow.is_deleted == False)  # noqa: E712
    )

    if q:
        query = query.filter(QuestionnaireFlow.name.ilike(f"%{q.strip()}%"))
    if flow_type:
        query = query.filter(QuestionnaireFlow.flow_type == flow_type)
    if status:
        query = query.filter(QuestionnaireFlow.status == status)

    total = query.count()
    flows = (
        query.order_by(QuestionnaireFlow.created_at.desc())
        .offset(skip)
        .limit(min(limit, 100))
        .all()
    )

    items: List[FlowOut] = []
    for f in flows:
        items.append(
            FlowOut(
                id=f.id,
                name=f.name,
                description=f.description,
                flow_type=f.flow_type,
                status=f.status.value,
                start_node_key=f.start_node_key,
                version=f.version,
                node_count=db.query(FlowNode).filter(FlowNode.flow_id == f.id).count(),
                created_at=f.created_at,
                created_by={
                    "id": f.created_by.id if f.created_by else None,
                    "name": _safe_user_name(f.created_by),
                    "email": getattr(f.created_by, "email", "") if f.created_by else "",
                },
            )
        )

    return FlowListOut(total=total, items=items)


# ============================================================
# ROUTES - GET DETAIL
# ============================================================
@router.get("/{flow_id}", response_model=FlowDetailOut)
def get_flow(
    flow_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    flow = (
        db.query(QuestionnaireFlow)
        .options(
            joinedload(QuestionnaireFlow.created_by),
            joinedload(QuestionnaireFlow.nodes).joinedload(FlowNode.options),
        )
        .filter(
            QuestionnaireFlow.id == flow_id,
            QuestionnaireFlow.is_deleted == False,  # noqa: E712
        )
        .first()
    )

    if not flow:
        raise HTTPException(404, "Flow not found")

    return FlowDetailOut(
        id=flow.id,
        name=flow.name,
        description=flow.description,
        flow_type=flow.flow_type,
        status=flow.status.value,
        start_node_key=flow.start_node_key,
        version=flow.version,
        created_at=flow.created_at,
        updated_at=flow.updated_at,
        created_by={
            "id": flow.created_by.id if flow.created_by else None,
            "name": _safe_user_name(flow.created_by),
            "email": getattr(flow.created_by, "email", "") if flow.created_by else "",
        },
        nodes=[
            FlowNodeOut(
                id=n.id,
                node_key=n.node_key,
                node_type=n.node_type.value,
                category=n.category,  # ✅ include category
                title=n.title,
                body_text=n.body_text,
                help_text=n.help_text,
                parent_node_key=n.parent_node_key,
                depth_level=n.depth_level,
                default_next_node_key=n.default_next_node_key,
                auto_next_node_key=n.auto_next_node_key,
                ui_ack_required=n.ui_ack_required,
                alert_severity=n.alert_severity.value if n.alert_severity else None,
                notify_admin=n.notify_admin,
                options=[
                    FlowOptionOut(
                        id=o.id,
                        display_order=o.display_order,
                        label=o.label,
                        value=o.value,
                        severity=o.severity.value,
                        news2_score=o.news2_score,
                        seriousness_points=o.seriousness_points,
                        next_node_key=o.next_node_key,
                    )
                    for o in n.options
                ],
            )
            for n in flow.nodes
        ],
    )


# ============================================================
# ROUTES - UPDATE
# ============================================================
@router.put("/{flow_id}", response_model=dict)
def update_flow(
    flow_id: int,
    data: FlowUpdateIn,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    flow = (
        db.query(QuestionnaireFlow)
        .options(joinedload(QuestionnaireFlow.nodes).joinedload(FlowNode.options))
        .filter(
            QuestionnaireFlow.id == flow_id,
            QuestionnaireFlow.is_deleted == False,  # noqa: E712
        )
        .first()
    )

    if not flow:
        raise HTTPException(404, "Flow not found")

    normalized_nodes = normalize_nodes_for_type(data.nodes)

    # ✅ ORM-safe delete (cascades options too)
    flow.nodes.clear()
    db.flush()

    flow.name = data.name
    flow.description = data.description
    flow.flow_type = data.flow_type
    flow.status = data.status
    flow.start_node_key = data.start_node_key
    flow.version += 1
    flow.updated_at = datetime.utcnow()

    db.flush()

    created_nodes = _create_nodes_from_data(flow.id, normalized_nodes, db)
    errors = validate_flow_integrity(flow, created_nodes)
    if errors:
        db.rollback()
        raise HTTPException(400, detail={"errors": errors})

    db.commit()
    db.refresh(flow)

    write_audit_log(
        db,
        "FLOW_UPDATED",
        user_id=current_user.id,
        request=request,
        details=f"flow_id={flow.id}, version={flow.version}",
    )
    return {"flow_id": flow.id, "version": flow.version, "message": "Flow updated successfully"}


# ============================================================
# ROUTES - DELETE
# ============================================================
@router.delete("/{flow_id}", response_model=dict)
def delete_flow(
    flow_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    flow = (
        db.query(QuestionnaireFlow)
        .filter(
            QuestionnaireFlow.id == flow_id,
            QuestionnaireFlow.is_deleted == False,  # noqa: E712
        )
        .first()
    )

    if not flow:
        raise HTTPException(404, "Flow not found")

    flow.is_deleted = True
    db.commit()

    write_audit_log(db, "FLOW_DELETED", user_id=current_user.id, request=request, details=f"flow_id={flow.id}")
    return {"message": "Flow deleted successfully"}


# ============================================================
# ROUTES - VALIDATE
# ============================================================
@router.get("/{flow_id}/validate", response_model=dict)
def validate_flow(
    flow_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    flow = (
        db.query(QuestionnaireFlow)
        .options(joinedload(QuestionnaireFlow.nodes).joinedload(FlowNode.options))
        .filter(
            QuestionnaireFlow.id == flow_id,
            QuestionnaireFlow.is_deleted == False,  # noqa: E712
        )
        .first()
    )

    if not flow:
        raise HTTPException(404, "Flow not found")

    errors = validate_flow_integrity(flow, flow.nodes)
    return {"flow_id": flow.id, "valid": len(errors) == 0, "errors": errors}
