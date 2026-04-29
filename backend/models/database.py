from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Text, ForeignKey
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from datetime import datetime
import os
from dotenv import load_dotenv

# Load env variables
load_dotenv()

# Project root = two levels up from this file (backend/models/database.py)
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA_DIR     = os.environ.get("DATA_DIR", os.path.join(PROJECT_ROOT, "data"))
os.makedirs(DATA_DIR, exist_ok=True)

# Database Logic: PostgreSQL (Production) or SQLite (Local)
DATABASE_URL = os.environ.get("DATABASE_URL")

if DATABASE_URL:
    # SQLAlchemy requires 'postgresql://' but many platforms (Render/Railway) provide 'postgres://'
    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
    
    # Engine for PostgreSQL
    engine = create_engine(DATABASE_URL)
else:
    # Fallback to SQLite for local development
    DATABASE_URL = f"sqlite:///{os.path.join(DATA_DIR, 'analyst_bot.db')}"
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class CrawlSession(Base):
    __tablename__ = "crawl_sessions"

    id = Column(Integer, primary_key=True, index=True)
    url = Column(String(500), nullable=False)
    site_name = Column(String(100), default="Unknown")
    total_items = Column(Integer, default=0)
    strategy = Column(String(50), default="auto")
    created_at = Column(DateTime, default=datetime.now)
    status = Column(String(20), default="success")

    products = relationship("Product", back_populates="session", cascade="all, delete-orphan")
    histories = relationship("AnalysisHistory", back_populates="session")


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("crawl_sessions.id"))
    name = Column(String(500), default="")
    price = Column(Float, default=0.0)
    price_raw = Column(String(100), default="")
    category = Column(String(200), default="Unknown")
    rating = Column(Float, default=0.0)
    url = Column(String(500), default="")
    image_url = Column(String(500), default="")
    extra_data = Column(Text, default="{}")
    created_at = Column(DateTime, default=datetime.now)

    session = relationship("CrawlSession", back_populates="products")


class AnalysisHistory(Base):
    __tablename__ = "analysis_history"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("crawl_sessions.id"), nullable=True)
    query = Column(String(500), default="")
    result = Column(Text, default="{}")
    insight = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.now)

    session = relationship("CrawlSession", back_populates="histories")


def create_tables():
    os.makedirs(DATA_DIR, exist_ok=True)
    Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
