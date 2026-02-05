from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker
from config import Settings
import logging

logger = logging.getLogger(__name__)

# Initialize settings
settings = Settings()

# Database URL
DATABASE_URL = f"mysql+pymysql://{settings.DB_USER}:{settings.DB_PASSWORD}@{settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}"

# Create engine with Aiven-specific settings
engine = create_engine(
    DATABASE_URL,
    echo=settings.DEBUG,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
    connect_args={
        "connect_timeout": 15,
        "charset": "utf8mb4",
        "autocommit": False
    }
)

# Create session factory
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

# Create base class for models
Base = declarative_base()


# Dependency for FastAPI routes
def get_db():
    """
    Get database session for dependency injection in FastAPI routes
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Function to initialize database tables
def init_db():
    """
    Create all database tables
    """
    try:
        logger.info("Creating database tables...")
        Base.metadata.create_all(bind=engine)
        logger.info("✅ Database tables created successfully")
    except Exception as e:
        logger.error(f"❌ Failed to create database tables: {str(e)}", exc_info=True)
        raise


# Function to check database connection
def check_db_connection():
    """
    Test database connection
    """
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
            logger.info("✅ Database connection successful")
            return True
    except Exception as e:
        logger.error(f"❌ Database connection failed: {e}")
        return False
