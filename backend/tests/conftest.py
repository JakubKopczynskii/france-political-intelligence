import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from models import Base
from seed_data import create_tables, seed_demo_data


@pytest.fixture
def test_db():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    create_tables(engine)
    with Session(engine) as db:
        seed_demo_data(db)
        yield db
