from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
import os

DATABASE_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "shipping_helper.db"
)
DATABASE_URL = f"sqlite:///{DATABASE_PATH}"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


os.makedirs(os.path.dirname(DATABASE_PATH), exist_ok=True)


def init_db():
    """Create all database tables."""
    # Import models to register them with Base.metadata
    from app.models.order import Order, OrderItem, PackagingType, ProductKnowledge
    Base.metadata.create_all(bind=engine)