from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from .config import settings # Ensure settings.DATABASE_URL is correctly configured

# Construct the database URL from settings
# Example: postgresql://user:password@host:port/database
SQLALCHEMY_DATABASE_URL = settings.DATABASE_URL

# For SQLite, you might need a different setup if you were to use it for local dev/testing
# if SQLALCHEMY_DATABASE_URL.startswith("sqlite"):
#     engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
# else:
#     engine = create_engine(SQLALCHEMY_DATABASE_URL)

engine = create_engine(SQLALCHEMY_DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Function to create all tables (useful for initial setup, but Alembic is preferred for migrations)
# def create_all_tables():
#     Base.metadata.create_all(bind=engine)
