from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from config import Settings

# Initialize settings
settings = Settings()

# Database URL
DATABASE_URL = f"mysql+pymysql://{settings.DB_USER}:{settings.DB_PASSWORD}@{settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}"

# Create engine
engine = create_engine(
    DATABASE_URL,
    echo=settings.DEBUG,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20
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
    Base.metadata.create_all(bind=engine)


# Function to check database connection
def check_db_connection():
    """
    Test database connection
    """
    try:
        with engine.connect() as conn:
            conn.execute("SELECT 1")
            return True
    except Exception as e:
        print(f"Database connection failed: {e}")
        return False
