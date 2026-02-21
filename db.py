import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# ============================================================
# Load .env for LOCAL development only
# (Railway ignores .env and injects env vars directly)
# ============================================================
load_dotenv()
print("DB ENV CHECK:", {k: os.getenv(k) for k in [
    "DATABASE_URL", "POSTGRES_URL", "POSTGRESQL_URL", "DATABASE_PUBLIC_URL"
]})
# ============================================================
# DATABASE URL (Railway + Neon + Local safe)
# ============================================================
DATABASE_URL = (
    os.getenv("DATABASE_URL")
    or os.getenv("POSTGRES_URL")
    or os.getenv("POSTGRESQL_URL")
    or os.getenv("DATABASE_PUBLIC_URL")
)

if not DATABASE_URL:
    # This error is intentional and GOOD — it tells us Railway
    # is not injecting the variable into THIS service
    raise RuntimeError(
        "DATABASE_URL environment variable is not set. "
        "Check Railway → Service → Variables → Apply → Redeploy."
    )

# Normalize old postgres:// URLs (SQLAlchemy requires postgresql://)
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# ============================================================
# SQLALCHEMY ENGINE
# ============================================================
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=300,   # important for Neon / serverless
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

Base = declarative_base()