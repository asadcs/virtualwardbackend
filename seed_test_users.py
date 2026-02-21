# seed_test_users.py
from datetime import datetime

from sqlalchemy.orm import Session

from db import SessionLocal
from auth import hash_password
from user import User
from role import Role

# ============================================================
# TEST USERS (ONLY THESE THREE)
# ============================================================
PATIENT = {"name": "Patient", "email": "patient2@gmail.com", "password": "password123", "role": "PATIENT"}
ADMIN   = {"name": "Admin",   "email": "deasad2019@gmail.com", "password": "12345678", "role": "ADMIN"}
DOCTOR  = {"name": "Doctor",  "email": "miangali927@gmail.com", "password": "Ahmed3772", "role": "DOCTOR"}

USERS = [PATIENT, ADMIN, DOCTOR]


def get_or_create_role(db: Session, role_name: str) -> Role:
    role = db.query(Role).filter(Role.name == role_name).first()
    if role:
        return role
    role = Role(name=role_name)
    db.add(role)
    db.commit()
    db.refresh(role)
    return role


def get_or_create_user(db: Session, name: str, email: str, password: str) -> User:
    email = email.lower()
    user = db.query(User).filter(User.email == email).first()
    if user:
        # optional: keep existing password as-is, but ensure name/email verified
        user.name = name
        user.is_email_verified = True
        user.email_verify_token_hash = None
        user.email_verify_expires_at = None
        db.commit()
        db.refresh(user)
        return user

    user = User(
        name=name,
        email=email,
        password=hash_password(password),
        is_email_verified=True,          # so login works without verify step
        email_verify_token_hash=None,
        email_verify_expires_at=None,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def ensure_role_assigned(db: Session, user: User, role: Role) -> None:
    # roles is a relationship list; just avoid duplicates
    if role not in user.roles:
        user.roles.append(role)
        db.commit()
        db.refresh(user)


def seed():
    db = SessionLocal()
    try:
        # 1) Ensure the three roles exist
        roles = {name: get_or_create_role(db, name) for name in ["ADMIN", "DOCTOR", "PATIENT"]}

        # 2) Create ONLY the three users and assign their role
        for u in USERS:
            user = get_or_create_user(db, u["name"], u["email"], u["password"])
            ensure_role_assigned(db, user, roles[u["role"]])
            print(f"✅ {u['role']}: {user.email} (id={user.id})")

        print("🎉 Done. Seeded 3 users + roles (idempotent).")

    finally:
        db.close()


if __name__ == "__main__":
    seed()