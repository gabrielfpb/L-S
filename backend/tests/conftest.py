import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from typing import Generator

from app.main import app # Main FastAPI app
from app.core.database import Base, get_db # For overriding DB dependency
from app.core.config import settings
from app.models import models # Import all models to ensure they are known to Base

# Use a separate test database (e.g., SQLite in-memory for speed, or a separate test Postgres DB)
SQLALCHEMY_DATABASE_URL_TEST = "sqlite:///:memory:"
# Or use a test specific postgres DB from settings, e.g.:
# SQLALCHEMY_DATABASE_URL_TEST = settings.DATABASE_URL.replace(settings.DB_NAME, settings.DB_NAME + "_test") if settings.DATABASE_URL else "sqlite:///:memory:"


engine = create_engine(SQLALCHEMY_DATABASE_URL_TEST, connect_args={"check_same_thread": False} if "sqlite" in SQLALCHEMY_DATABASE_URL_TEST else {})

# Create tables in the test database once per session
@pytest.fixture(scope="session", autouse=True) # autouse=True to ensure this runs for the session
def create_test_tables():
    Base.metadata.create_all(bind=engine)
    yield
    # Base.metadata.drop_all(bind=engine) # Optional: drop tables after all tests in session

TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="function")
def db() -> Generator[Session, None, None]:
    connection = engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)

    yield session # Provide the session to the test

    session.close()
    transaction.rollback() # Rollback any changes made during the test
    connection.close()

@pytest.fixture(scope="function")
def client(db: Session) -> Generator[TestClient, None, None]:
    def override_get_db():
        try:
            yield db
        finally:
            # db.close() # The 'db' fixture itself should handle closing the session after rollback.
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    del app.dependency_overrides[get_db] # Clean up override


@pytest.fixture(scope="function")
def authenticated_client(client: TestClient, db: Session):
    from app.services.user_service import create_user, get_user_by_username
    from app.api.schemas.user_schemas import UserCreate
    from app.core.security import create_access_token

    test_username = "testuserfixture"
    test_user_data = UserCreate(username=test_username, email="testfixture@example.com", password="testpassword")

    user = get_user_by_username(db, username=test_username)
    if not user:
        user = create_user(db, test_user_data)

    token_data = {"sub": user.username, "id": user.id}
    access_token = create_access_token(data=token_data)

    client.headers["Authorization"] = f"Bearer {access_token}"
    return client
