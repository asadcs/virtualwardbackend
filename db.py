# from sqlalchemy import create_engine
# from sqlalchemy.orm import sessionmaker, declarative_base

# # ============================================================
# # 🚨 DEMO ONLY – HARDCODED DATABASE URL
# # REMOVE AFTER DEMO
# # ============================================================

# DATABASE_URL = (
#     "postgresql://neondb_owner:npg_fsAZJp1RlcC5@"
#     "ep-wild-haze-aiqb32h9-pooler.c-4.us-east-1.aws.neon.tech/"
#     "neondb?sslmode=require&channel_binding=require"
# )

# engine = create_engine(
#     DATABASE_URL,
#     pool_pre_ping=True,
#     pool_recycle=300,
# )

# SessionLocal = sessionmaker(
#     autocommit=False,
#     autoflush=False,
#     bind=engine,
# )

# Base = declarative_base()


from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# ⚠️ DEMO ONLY – REMOVE AFTER
DATABASE_URL = "postgresql://neondb_owner:npg_fsAZJp1RlcC5@ep-wild-haze-aiqb32h9-pooler.c-4.us-east-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require"

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

Base = declarative_base()