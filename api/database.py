from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from config.settings import settings

try:
    engine = create_engine(
        settings.database_url,
        pool_pre_ping=True,
        echo=settings.DEBUG
    )
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
except Exception as e:
    print(f"Warning: Could not create database engine: {e}")
    engine = None
    SessionLocal = None

Base = declarative_base()

def get_db():
    """Dependency for database sessions."""
    if SessionLocal is None:
        raise RuntimeError("Database is not configured")
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
