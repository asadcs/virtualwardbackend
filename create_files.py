# # create_files.py
# import os

# files = {
#     "db.py": """
# from sqlalchemy import create_engine
# from sqlalchemy.orm import sessionmaker, declarative_base

# DATABASE_URL = "sqlite:///./app.db"   # Use Postgres in production

# engine = create_engine(
#     DATABASE_URL, connect_args={"check_same_thread": False}
# )

# SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)

# Base = declarative_base()
# """,

#     "user.py": """
# from sqlalchemy import Column, Integer, String, Boolean, TIMESTAMP
# from sqlalchemy.orm import relationship
# from datetime import datetime
# from db import Base

# class User(Base):
#     __tablename__ = "users"

#     id = Column(Integer, primary_key=True, index=True)
#     email = Column(String(255), unique=True, nullable=False)
#     password_hash = Column(String(255), nullable=False)
#     full_name = Column(String(255))
#     status = Column(String(20), default="active")
#     is_super_admin = Column(Boolean, default=False)
#     created_at = Column(TIMESTAMP, default=datetime.utcnow)

#     roles = relationship("Role", secondary="user_roles", back_populates="users")
# """,

#     "role.py": """
# from sqlalchemy import Column, Integer, String, Boolean, TIMESTAMP, Table, ForeignKey
# from sqlalchemy.orm import relationship
# from datetime import datetime
# from db import Base

# class Role(Base):
#     __tablename__ = "roles"

#     id = Column(Integer, primary_key=True, index=True)
#     name = Column(String(100), unique=True, nullable=False)
#     display_name = Column(String(100))
#     is_system = Column(Boolean, default=False)
#     priority = Column(Integer, default=0)
#     created_at = Column(TIMESTAMP, default=datetime.utcnow)

#     users = relationship("User", secondary="user_roles", back_populates="roles")

# # Many-to-many table
# user_roles = Table(
#     "user_roles",
#     Base.metadata,
#     Column("user_id", Integer, ForeignKey("users.id")),
#     Column("role_id", Integer, ForeignKey("roles.id")),
# )
# """,

#     "main.py": """
# from fastapi import FastAPI, Depends, HTTPException
# from fastapi.security import OAuth2PasswordRequestForm
# import jwt
# from datetime import datetime, timedelta
# from db import Base, engine, SessionLocal
# from user import User
# from role import Role
# from sqlalchemy.orm import Session
# from passlib.context import CryptContext

# app = FastAPI()

# Base.metadata.create_all(bind=engine)

# pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
# JWT_SECRET = "MY_SECRET_KEY"

# def get_db():
#     db = SessionLocal()
#     try:
#         yield db
#     finally:
#         db.close()

# def create_access_token(data: dict, expires_minutes=15):
#     payload = data.copy()
#     payload["exp"] = datetime.utcnow() + timedelta(minutes=expires_minutes)
#     return jwt.encode(payload, JWT_SECRET, algorithm="HS256")

# @app.post("/register")
# def register(email: str, password: str, db: Session = Depends(get_db)):
#     hashed = pwd_context.hash(password)
#     user = User(email=email, password_hash=hashed)
#     db.add(user)
#     db.commit()
#     db.refresh(user)
#     return {"message": "User created", "user_id": user.id}

# @app.post("/login")
# def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
#     user = db.query(User).filter(User.email == form.username).first()
#     if not user or not pwd_context.verify(form.password, user.password_hash):
#         raise HTTPException(400, "Invalid credentials")

#     token = create_access_token({
#         "sub": user.id,
#         "email": user.email,
#     })

#     return {"access_token": token, "token_type": "bearer"}

# @app.post("/role")
# def create_role(name: str, display_name: str, db: Session = Depends(get_db)):
#     role = Role(name=name, display_name=display_name)
#     db.add(role)
#     db.commit()
#     return {"message": "Role created"}

# @app.post("/assign-role")
# def assign_role(user_id: int, role_id: int, db: Session = Depends(get_db)):
#     user = db.query(User).get(user_id)
#     role = db.query(Role).get(role_id)

#     if not user or not role:
#         raise HTTPException(404, "User or Role not found")

#     user.roles.append(role)
#     db.commit()
#     return {"message": "Role assigned to user"}
# """
# }

# for filename, content in files.items():
#     with open(filename, "w") as f:
#         f.write(content.strip())

# print("All files created successfully!")

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL is not set")

# Normalize just in case
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()