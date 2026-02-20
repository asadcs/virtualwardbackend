# import time
# import jwt
# import secrets
# import hashlib
# from datetime import datetime, timedelta
# from typing import Optional, Dict, Tuple

# from fastapi import HTTPException, Depends, Request
# from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
# from passlib.context import CryptContext
# from sqlalchemy.orm import Session
# from sqlalchemy import (
#     Column,
#     Integer,
#     String,
#     DateTime,
#     Boolean,
#     ForeignKey,
#     Text,
# )

# from db import SessionLocal, Base

# # ============================================================
# # CONFIG
# # ============================================================
# SECRET_KEY = "CHANGE_THIS_SECRET_KEY"  # move to env later
# ALGORITHM = "HS256"
# ACCESS_TOKEN_EXPIRE_MINUTES = 15
# REFRESH_TOKEN_EXPIRE_DAYS = 7

# pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
# security = HTTPBearer()

# # ============================================================
# # DB DEPENDENCY
# # ============================================================
# def get_db():
#     db = SessionLocal()
#     try:
#         yield db
#     finally:
#         db.close()

# # ============================================================
# # PASSWORD HASHING (bcrypt – passwords only!)
# # ============================================================
# def hash_password(password: str) -> str:
#     if len(password.encode("utf-8")) > 72:
#         raise HTTPException(422, "Password must be 72 bytes or fewer")
#     return pwd_context.hash(password)

# def verify_password(password: str, hashed: str) -> bool:
#     return pwd_context.verify(password, hashed)

# # ============================================================
# # TOKEN HASHING (SHA-256 – refresh tokens)
# # ============================================================
# def hash_token(token: str) -> str:
#     return hashlib.sha256(token.encode("utf-8")).hexdigest()

# def verify_token(token: str, token_hash: str) -> bool:
#     return hash_token(token) == token_hash

# # ============================================================
# # MODELS
# # ============================================================
# class RefreshToken(Base):
#     __tablename__ = "refresh_tokens"

#     id = Column(Integer, primary_key=True)
#     user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
#     token_hash = Column(String(64), index=True, nullable=False)
#     expires_at = Column(DateTime, nullable=False)
#     revoked = Column(Boolean, default=False)


# class AuditLog(Base):
#     __tablename__ = "audit_logs"

#     id = Column(Integer, primary_key=True)
#     user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
#     action = Column(String(80), nullable=False)
#     ip_address = Column(String(64), nullable=True)
#     user_agent = Column(String(255), nullable=True)
#     details = Column(Text, nullable=True)
#     created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

# # ============================================================
# # AUDIT LOG HELPER
# # ============================================================
# def write_audit_log(
#     db: Session,
#     action: str,
#     user_id: Optional[int] = None,
#     request: Optional[Request] = None,
#     details: Optional[str] = None,
# ):
#     ip = None
#     ua = None
#     if request is not None:
#         ip = request.client.host if request.client else None
#         ua = request.headers.get("user-agent")

#     row = AuditLog(
#         user_id=user_id,
#         action=action,
#         ip_address=ip,
#         user_agent=ua,
#         details=details,
#     )
#     db.add(row)
#     db.commit()

# # ============================================================
# # JWT HELPERS
# # ============================================================
# def create_access_token(user_id: int) -> str:
#     expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
#     payload = {
#         "sub": str(user_id),
#         "type": "access",
#         "exp": expire,
#     }
#     return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

# def generate_refresh_token() -> str:
#     return secrets.token_urlsafe(48)

# def create_refresh_token(db: Session, user_id: int, raw_token: str) -> RefreshToken:
#     row = RefreshToken(
#         user_id=user_id,
#         token_hash=hash_token(raw_token),
#         expires_at=datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS),
#         revoked=False,
#     )
#     db.add(row)
#     db.commit()
#     db.refresh(row)
#     return row

# def verify_refresh_token(db: Session, raw_token: str) -> RefreshToken:
#     token_hash = hash_token(raw_token)

#     token = (
#         db.query(RefreshToken)
#         .filter(
#             RefreshToken.token_hash == token_hash,
#             RefreshToken.revoked == False,
#         )
#         .first()
#     )

#     if not token:
#         raise HTTPException(401, "Invalid refresh token")

#     if token.expires_at < datetime.utcnow():
#         token.revoked = True
#         db.commit()
#         raise HTTPException(401, "Refresh token expired")

#     return token

# def revoke_refresh_token(db: Session, raw_token: str):
#     token_hash = hash_token(raw_token)
#     token = (
#         db.query(RefreshToken)
#         .filter(RefreshToken.token_hash == token_hash)
#         .first()
#     )
#     if token:
#         token.revoked = True
#         db.commit()

# # ============================================================
# # AUTH DEPENDENCIES
# # ============================================================
# def get_current_user(
#     credentials: HTTPAuthorizationCredentials = Depends(security),
#     db: Session = Depends(get_db),
# ):
#     token = credentials.credentials

#     try:
#         payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
#         if payload.get("type") != "access":
#             raise HTTPException(401, "Invalid token type")

#         sub = payload.get("sub")
#         if not sub:
#             raise HTTPException(401, "Invalid token")

#         user_id = int(sub)

#     except jwt.ExpiredSignatureError:
#         raise HTTPException(401, "Token expired")
#     except Exception:
#         raise HTTPException(401, "Invalid token")

#     from user import User  # local import to avoid circular dependency

#     user = db.query(User).filter(User.id == user_id).first()
#     if not user:
#         raise HTTPException(404, "User not found")

#     return user

# def require_admin(current_user=Depends(get_current_user)):
#     roles = [r.name for r in current_user.roles]
#     if "ADMIN" not in roles:
#         raise HTTPException(403, "Admin access required")
#     return current_user

# # ============================================================
# # RATE LIMITING (dev-friendly)
# # ============================================================
# _rate_store: Dict[str, Tuple[int, float]] = {}

# def rate_limit(limit: int, window_seconds: int):
#     """
#     Usage: Depends(rate_limit(10, 60))
#     """
#     def _dep(request: Request):
#         ip = request.client.host if request.client else "unknown"
#         key = f"{ip}:{request.url.path}"
#         now = time.time()

#         count, start = _rate_store.get(key, (0, now))

#         if now - start >= window_seconds:
#             _rate_store[key] = (1, now)
#             return

#         if count >= limit:
#             raise HTTPException(429, "Too many requests")

#         _rate_store[key] = (count + 1, start)

#     return _dep


import time
import jwt
import secrets
import hashlib
from datetime import datetime, timedelta
from typing import Optional, Dict, Tuple

from fastapi import HTTPException, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from passlib.context import CryptContext
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    Boolean,
    ForeignKey,
    Text,
)

from db import SessionLocal, Base

# ============================================================
# CONFIG
# ============================================================
SECRET_KEY = "CHANGE_THIS_SECRET_KEY"  # move to env later
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 15
REFRESH_TOKEN_EXPIRE_DAYS = 7

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()

# ============================================================
# DB DEPENDENCY
# ============================================================
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ============================================================
# PASSWORD HASHING (bcrypt – passwords only!)
# ============================================================
def hash_password(password: str) -> str:
    if len(password.encode("utf-8")) > 72:
        raise HTTPException(422, "Password must be 72 bytes or fewer")
    return pwd_context.hash(password)

def verify_password(password: str, hashed: str) -> bool:
    return pwd_context.verify(password, hashed)

# ============================================================
# TOKEN HASHING (SHA-256 – refresh tokens)
# ============================================================
def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()

def verify_token(token: str, token_hash: str) -> bool:
    return hash_token(token) == token_hash

# ============================================================
# MODELS
# ============================================================
class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    token_hash = Column(String(64), index=True, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    revoked = Column(Boolean, default=False)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    action = Column(String(80), nullable=False)
    ip_address = Column(String(64), nullable=True)
    user_agent = Column(String(255), nullable=True)
    details = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

# ============================================================
# AUDIT LOG HELPER
# ============================================================
def write_audit_log(
    db: Session,
    action: str,
    user_id: Optional[int] = None,
    request: Optional[Request] = None,
    details: Optional[str] = None,
):
    ip = None
    ua = None
    if request is not None:
        ip = request.client.host if request.client else None
        ua = request.headers.get("user-agent")

    row = AuditLog(
        user_id=user_id,
        action=action,
        ip_address=ip,
        user_agent=ua,
        details=details,
    )
    db.add(row)
    db.commit()

# ============================================================
# JWT HELPERS
# ============================================================
def create_access_token(user_id: int) -> str:
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {
        "sub": str(user_id),
        "type": "access",
        "exp": expire,
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def generate_refresh_token() -> str:
    return secrets.token_urlsafe(48)

def create_refresh_token(db: Session, user_id: int, raw_token: str) -> RefreshToken:
    row = RefreshToken(
        user_id=user_id,
        token_hash=hash_token(raw_token),
        expires_at=datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS),
        revoked=False,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row

def verify_refresh_token(db: Session, raw_token: str) -> RefreshToken:
    token_hash = hash_token(raw_token)

    token = (
        db.query(RefreshToken)
        .filter(
            RefreshToken.token_hash == token_hash,
            RefreshToken.revoked == False,
        )
        .first()
    )

    if not token:
        raise HTTPException(401, "Invalid refresh token")

    if token.expires_at < datetime.utcnow():
        token.revoked = True
        db.commit()
        raise HTTPException(401, "Refresh token expired")

    return token

def revoke_refresh_token(db: Session, raw_token: str):
    token_hash = hash_token(raw_token)
    token = (
        db.query(RefreshToken)
        .filter(RefreshToken.token_hash == token_hash)
        .first()
    )
    if token:
        token.revoked = True
        db.commit()

# ============================================================
# AUTH DEPENDENCIES
# ============================================================
def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
):
    token = credentials.credentials

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("type") != "access":
            raise HTTPException(401, "Invalid token type")

        sub = payload.get("sub")
        if not sub:
            raise HTTPException(401, "Invalid token")

        user_id = int(sub)

    except jwt.ExpiredSignatureError:
        raise HTTPException(401, "Token expired")
    except Exception:
        raise HTTPException(401, "Invalid token")

    from user import User  # local import to avoid circular dependency

    # ✅ IMPORTANT: load roles eagerly (fixes admin 403)
    user = (
        db.query(User)
        .options(joinedload(User.roles))
        .filter(User.id == user_id)
        .first()
    )

    if not user:
        raise HTTPException(404, "User not found")

    return user

def require_admin(current_user=Depends(get_current_user)):
    role_names = {getattr(r, "name", str(r)) for r in (getattr(current_user, "roles", []) or [])}
    if "ADMIN" not in role_names:
        raise HTTPException(403, "Admin access required")
    return current_user

# ============================================================
# RATE LIMITING (dev-friendly)
# ============================================================
_rate_store: Dict[str, Tuple[int, float]] = {}

def rate_limit(limit: int, window_seconds: int):
    """
    Usage: Depends(rate_limit(10, 60))
    """
    def _dep(request: Request):
        ip = request.client.host if request.client else "unknown"
        key = f"{ip}:{request.url.path}"
        now = time.time()

        count, start = _rate_store.get(key, (0, now))

        if now - start >= window_seconds:
            _rate_store[key] = (1, now)
            return

        if count >= limit:
            raise HTTPException(429, "Too many requests")

        _rate_store[key] = (count + 1, start)

    return _dep
