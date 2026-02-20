from datetime import datetime, timedelta
import hashlib
import secrets
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session, relationship
from sqlalchemy import Column, Integer, String, Table, ForeignKey, Boolean, DateTime
from pydantic import BaseModel, EmailStr, Field

from db import Base
from auth import (
    get_db,
    hash_password,
    verify_password,
    create_access_token,
    generate_refresh_token,
    create_refresh_token,
    verify_refresh_token,
    revoke_refresh_token,
    get_current_user,
    rate_limit,
    write_audit_log,
)

router = APIRouter()

# ============================================================
# MANY-TO-MANY RELATIONSHIP TABLE
# ============================================================
user_roles = Table(
    "user_roles",
    Base.metadata,
    Column("user_id", Integer, ForeignKey("users.id")),
    Column("role_id", Integer, ForeignKey("roles.id")),
)

# ============================================================
# SQLALCHEMY MODELS
# ============================================================
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    email = Column(String(120), unique=True, nullable=False, index=True)
    password = Column(String(255), nullable=False)

    is_email_verified = Column(Boolean, default=False, nullable=False)

    # store SHA256 of verification token (NOT bcrypt)
    email_verify_token_hash = Column(String(64), nullable=True, index=True)
    email_verify_expires_at = Column(DateTime, nullable=True)

    roles = relationship("Role", secondary=user_roles, back_populates="users")


class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # store SHA256 of reset token (NOT bcrypt)
    token_hash = Column(String(64), nullable=False, index=True)

    expires_at = Column(DateTime, nullable=False)
    used = Column(Boolean, default=False, nullable=False)

# ============================================================
# PYDANTIC SCHEMAS
# ============================================================
class UserCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)  # bcrypt limit


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class TokenRefreshRequest(BaseModel):
    refresh_token: str


class AssignRoleRequest(BaseModel):
    user_id: int
    role_id: int


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8, max_length=72)  # bcrypt limit


class RequestPasswordReset(BaseModel):
    email: EmailStr


class ResetPassword(BaseModel):
    reset_token: str
    new_password: str = Field(min_length=8, max_length=72)  # bcrypt limit


class VerifyEmailRequest(BaseModel):
    token: str

# ============================================================
# HELPERS (SHA-256 token hashing)
# ============================================================
def _new_dev_token() -> str:
    return secrets.token_urlsafe(48)

def _sha256(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()

# ============================================================
# ROUTES
# ============================================================

# -----------------------------
# Register
# -----------------------------
@router.post("/register", dependencies=[Depends(rate_limit(10, 60))])
def register_user(data: UserCreate, request: Request, db: Session = Depends(get_db)):
    email = data.email.lower()

    if db.query(User).filter(User.email == email).first():
        raise HTTPException(400, "Email already exists")

    raw_verify = _new_dev_token()

    user = User(
        name=data.name,
        email=email,
        password=hash_password(data.password),  # bcrypt (OK)
        email_verify_token_hash=_sha256(raw_verify),  # SHA256 (OK)
        email_verify_expires_at=datetime.utcnow() + timedelta(hours=24),
        is_email_verified=False,
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    write_audit_log(db, "USER_REGISTER", user_id=user.id, request=request)

    return {
        "message": "User registered. Verify your email.",
        "user_id": user.id,
        "dev_email_verification_token": raw_verify,
    }

# -----------------------------
# Verify Email
# -----------------------------
@router.post("/verify-email", dependencies=[Depends(rate_limit(20, 60))])
def verify_email(payload: VerifyEmailRequest, request: Request, db: Session = Depends(get_db)):
    token_hash = _sha256(payload.token)

    user = (
        db.query(User)
        .filter(
            User.is_email_verified == False,
            User.email_verify_token_hash == token_hash,
        )
        .first()
    )

    if not user:
        raise HTTPException(400, "Invalid verification token")

    if user.email_verify_expires_at and user.email_verify_expires_at < datetime.utcnow():
        raise HTTPException(400, "Verification token expired")

    user.is_email_verified = True
    user.email_verify_token_hash = None
    user.email_verify_expires_at = None
    db.commit()

    write_audit_log(db, "EMAIL_VERIFIED", user_id=user.id, request=request)
    return {"message": "Email verified successfully"}

# -----------------------------
# Login
# -----------------------------
@router.post("/login", dependencies=[Depends(rate_limit(15, 60))])
def login(data: UserLogin, request: Request, db: Session = Depends(get_db)):
    email = data.email.lower()
    user = db.query(User).filter(User.email == email).first()

    if not user or not verify_password(data.password, user.password):
        write_audit_log(db, "LOGIN_FAILED", request=request)
        raise HTTPException(401, "Invalid credentials")

    if not user.is_email_verified:
        raise HTTPException(403, "Email not verified")

    # IMPORTANT: create_access_token(user_id)  (matches corrected auth.py)
    access_token = create_access_token(user.id)

    raw_refresh = generate_refresh_token()
    create_refresh_token(db, user.id, raw_refresh)

    write_audit_log(db, "LOGIN_SUCCESS", user_id=user.id, request=request)

    return {"access_token": access_token, "refresh_token": raw_refresh}

# -----------------------------
# Refresh Token
# -----------------------------
@router.post("/refresh", dependencies=[Depends(rate_limit(30, 60))])
def refresh_token(payload: TokenRefreshRequest, request: Request, db: Session = Depends(get_db)):
    token_row = verify_refresh_token(db, payload.refresh_token)

    new_access = create_access_token(token_row.user_id)
    new_refresh = generate_refresh_token()
    create_refresh_token(db, token_row.user_id, new_refresh)

    token_row.revoked = True
    db.commit()

    write_audit_log(db, "TOKEN_REFRESH", user_id=token_row.user_id, request=request)

    return {"access_token": new_access, "refresh_token": new_refresh}

# -----------------------------
# Logout
# -----------------------------
@router.post("/logout")
def logout(payload: TokenRefreshRequest, request: Request, db: Session = Depends(get_db)):
    # Either verify & revoke, or just revoke if you want idempotent logout
    token_row = verify_refresh_token(db, payload.refresh_token)
    token_row.revoked = True
    db.commit()

    write_audit_log(db, "LOGOUT", user_id=token_row.user_id, request=request)
    return {"message": "Logged out successfully"}

# -----------------------------
# Current User
# -----------------------------
@router.get("/me")
def me(current_user=Depends(get_current_user)):
    return {
        "id": current_user.id,
        "name": current_user.name,
        "email": current_user.email,
        "email_verified": current_user.is_email_verified,
        "roles": [r.name for r in getattr(current_user, "roles", [])],
    }

# -----------------------------
# List Users (pagination & filters)
# -----------------------------
@router.get("/")
def list_users(
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 20,
    name: Optional[str] = None,
    email: Optional[str] = None,
):
    q = db.query(User)

    if name:
        q = q.filter(User.name.ilike(f"%{name}%"))
    if email:
        q = q.filter(User.email.ilike(f"%{email}%"))

    total = q.count()
    users = q.offset(skip).limit(min(limit, 100)).all()

    return {
        "total": total,
        "items": [
            {
                "id": u.id,
                "name": u.name,
                "email": u.email,
                "roles": [r.name for r in u.roles],
            }
            for u in users
        ],
    }

# -----------------------------
# Change Password
# -----------------------------
@router.post("/change-password")
def change_password(
    payload: ChangePasswordRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    if not verify_password(payload.current_password, current_user.password):
        raise HTTPException(400, "Current password is incorrect")

    current_user.password = hash_password(payload.new_password)
    db.commit()

    write_audit_log(db, "PASSWORD_CHANGED", user_id=current_user.id, request=request)
    return {"message": "Password changed successfully"}

# -----------------------------
# Password Reset (Request)
# -----------------------------
@router.post("/request-password-reset", dependencies=[Depends(rate_limit(10, 60))])
def request_password_reset(payload: RequestPasswordReset, request: Request, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email.lower()).first()
    message = "If the email exists, a reset token was generated."

    if not user:
        return {"message": message}

    raw = _new_dev_token()

    token = PasswordResetToken(
        user_id=user.id,
        token_hash=_sha256(raw),  # SHA256 (OK)
        expires_at=datetime.utcnow() + timedelta(minutes=30),
        used=False,
    )
    db.add(token)
    db.commit()

    write_audit_log(db, "PASSWORD_RESET_REQUEST", user_id=user.id, request=request)

    # IMPORTANT: tests expect this key
    return {"message": message, "dev_reset_token": raw}

# -----------------------------
# Password Reset (Confirm)
# -----------------------------
@router.post("/reset-password", dependencies=[Depends(rate_limit(10, 60))])
def reset_password(payload: ResetPassword, request: Request, db: Session = Depends(get_db)):
    token_hash = _sha256(payload.reset_token)

    t = (
        db.query(PasswordResetToken)
        .filter(
            PasswordResetToken.used == False,
            PasswordResetToken.token_hash == token_hash,
        )
        .first()
    )

    if not t:
        raise HTTPException(400, "Invalid reset token")

    if t.expires_at < datetime.utcnow():
        t.used = True
        db.commit()
        raise HTTPException(400, "Reset token expired")

    user = db.query(User).filter(User.id == t.user_id).first()
    if not user:
        raise HTTPException(404, "User not found")

    user.password = hash_password(payload.new_password)
    t.used = True
    db.commit()

    write_audit_log(db, "PASSWORD_RESET_SUCCESS", user_id=user.id, request=request)
    return {"message": "Password reset successful"}

# -----------------------------
# Assign Role
# -----------------------------
@router.post("/assign-role")
def assign_role(data: AssignRoleRequest, request: Request, db: Session = Depends(get_db)):
    from role import Role

    user = db.query(User).filter(User.id == data.user_id).first()
    role = db.query(Role).filter(Role.id == data.role_id).first()

    if not user or not role:
        raise HTTPException(404, "User or role not found")

    if role not in user.roles:
        user.roles.append(role)
        db.commit()

    write_audit_log(db, "ROLE_ASSIGNED", user_id=user.id, request=request)
    return {"message": "Role assigned"}

# -----------------------------
# Remove Role
# -----------------------------
@router.post("/remove-role")
def remove_role(data: AssignRoleRequest, request: Request, db: Session = Depends(get_db)):
    from role import Role

    user = db.query(User).filter(User.id == data.user_id).first()
    role = db.query(Role).filter(Role.id == data.role_id).first()

    if not user or not role:
        raise HTTPException(404, "User or role not found")

    if role in user.roles:
        user.roles.remove(role)
        db.commit()

    write_audit_log(db, "ROLE_REMOVED", user_id=user.id, request=request)
    return {"message": "Role removed"}
