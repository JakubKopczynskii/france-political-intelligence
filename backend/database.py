import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from typing import Generator

# Compute DB path relative to backend dir
_backend_dir = os.path.dirname(os.path.abspath(__file__))
_data_dir = os.path.join(_backend_dir, "..", "data")
os.makedirs(_data_dir, exist_ok=True)
_db_path = os.path.join(_data_dir, "france_intel.db")

DATABASE_URL = f"sqlite:///{_db_path}"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    echo=False,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db() -> Generator:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
