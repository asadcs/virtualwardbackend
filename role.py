from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session, relationship
from sqlalchemy import Column, Integer, String
from pydantic import BaseModel

from db import Base
from auth import get_db, require_admin, rate_limit, write_audit_log
from user import user_roles

router = APIRouter()

# ============================================================
# SQLALCHEMY ROLE MODEL
# ============================================================
class Role(Base):
    __tablename__ = "roles"

    id = Column(Integer, primary_key=True)
    name = Column(String(100), unique=True, nullable=False)

    users = relationship("User", secondary=user_roles, back_populates="roles")

# ============================================================
# SCHEMAS
# ============================================================
class RoleCreate(BaseModel):
    name: str

class RoleUpdate(BaseModel):
    name: str

# ============================================================
# ROUTES
# ============================================================

@router.post("/", dependencies=[Depends(rate_limit(20, 60))])
def create_role(
    data: RoleCreate,
    request: Request,
    db: Session = Depends(get_db),
    admin=Depends(require_admin),
):
    existing = db.query(Role).filter(Role.name == data.name).first()
    if existing:
        raise HTTPException(400, "Role already exists")

    role = Role(name=data.name)
    db.add(role)
    db.commit()
    db.refresh(role)

    write_audit_log(db, "ROLE_CREATED", user_id=admin.id, request=request, details=f"role={role.name}")
    return {"message": "Role created successfully", "role_id": role.id}


@router.get("/")
def list_roles(
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 20,
    name: str | None = None,
):
    q = db.query(Role)
    if name:
        q = q.filter(Role.name.ilike(f"%{name}%"))

    total = q.count()
    roles = q.offset(skip).limit(min(limit, 100)).all()

    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "items": [{"id": r.id, "name": r.name, "users_count": len(r.users)} for r in roles],
    }


@router.get("/{role_id}")
def get_role(role_id: int, db: Session = Depends(get_db)):
    role = db.query(Role).filter(Role.id == role_id).first()
    if not role:
        raise HTTPException(404, "Role not found")

    return {
        "id": role.id,
        "name": role.name,
        "users": [{"id": u.id, "email": u.email} for u in role.users],
    }


@router.put("/{role_id}", dependencies=[Depends(rate_limit(20, 60))])
def update_role(
    role_id: int,
    data: RoleUpdate,
    request: Request,
    db: Session = Depends(get_db),
    admin=Depends(require_admin),
):
    role = db.query(Role).filter(Role.id == role_id).first()
    if not role:
        raise HTTPException(404, "Role not found")

    old = role.name
    role.name = data.name
    db.commit()

    write_audit_log(db, "ROLE_UPDATED", user_id=admin.id, request=request, details=f"{old} -> {role.name}")
    return {"message": "Role updated successfully"}


@router.delete("/{role_id}", dependencies=[Depends(rate_limit(20, 60))])
def delete_role(
    role_id: int,
    request: Request,
    db: Session = Depends(get_db),
    admin=Depends(require_admin),
):
    role = db.query(Role).filter(Role.id == role_id).first()
    if not role:
        raise HTTPException(404, "Role not found")

    name = role.name
    db.delete(role)
    db.commit()

    write_audit_log(db, "ROLE_DELETED", user_id=admin.id, request=request, details=f"role={name}")
    return {"message": "Role deleted successfully"}
