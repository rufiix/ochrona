import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.main import app
from app.models import Base
from app.database import get_db

# Use a file-based SQLite database for testing
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Dependency to override the get_db dependency in the main app
def override_get_db():
    """
    Provides a test database session that is isolated from the production database.
    """
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

# Apply the override to the FastAPI app
app.dependency_overrides[get_db] = override_get_db

@pytest.fixture(scope="session", autouse=True)
def setup_test_database():
    """
    Fixture to set up and tear down the test database for the entire session.
    """
    if os.path.exists("./test.db"):
        os.remove("./test.db")
    Base.metadata.create_all(bind=engine)
    yield
    if os.path.exists("./test.db"):
        os.remove("./test.db")

@pytest.fixture(scope="function")
def client():
    """
    Provides a TestClient instance for making requests to the app.
    This client uses the overridden database dependency.
    """
    # Before each test, we clear all data from tables to ensure isolation
    with engine.connect() as connection:
        with connection.begin():
            for table in reversed(Base.metadata.sorted_tables):
                connection.execute(table.delete())

    with TestClient(app) as c:
        yield c