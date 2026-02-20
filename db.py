from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# ---------- POSTGRES CONFIGURATION ----------
USER = "asad"
PASSWORD = "asad"
HOST = "localhost"
PORT = "5432"
DB_NAME = "virtualward"

DATABASE_URL = f"postgresql+psycopg2://{USER}:{PASSWORD}@{HOST}:{PORT}/{DB_NAME}"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()
