"""
Database connection manager
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import NullPool
from contextlib import contextmanager
from typing import Generator
import logging

from src.database.models import Base
from src.utils.config import config

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Singleton database manager"""
    
    _instance = None
    _engine = None
    _session_factory = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._engine is None:
            self._initialize_engine()
    
    def _initialize_engine(self):
        """Initialize SQLAlchemy engine"""
        db_config = config.database
        
        # Build connection string
        connection_string = (
            f"postgresql://{db_config['user']}:{db_config['password']}"
            f"@{db_config['host']}:{db_config['port']}/{db_config['name']}"
        )
        
        # Create engine
        self._engine = create_engine(
            connection_string,
            echo=False,  # Set to True for SQL debugging
            pool_pre_ping=True,  # Verify connections before using
            pool_size=10,
            max_overflow=20,
        )
        
        # Create session factory
        self._session_factory = sessionmaker(bind=self._engine)
        
        logger.info(f"Database engine initialized: {db_config['host']}:{db_config['port']}/{db_config['name']}")
    
    @property
    def engine(self):
        """Get SQLAlchemy engine"""
        return self._engine
    
    @contextmanager
    def get_session(self) -> Generator[Session, None, None]:
        """
        Context manager for database sessions
        
        Usage:
            with db_manager.get_session() as session:
                track = session.query(Track).first()
        """
        session = self._session_factory()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Database session error: {e}")
            raise
        finally:
            session.close()
    
    def create_all_tables(self):
        """Create all tables in the database"""
        try:
            Base.metadata.create_all(self._engine)
            logger.info("All database tables created successfully")
        except Exception as e:
            logger.error(f"Error creating tables: {e}")
            raise
    
    def drop_all_tables(self):
        """Drop all tables (use with caution!)"""
        try:
            Base.metadata.drop_all(self._engine)
            logger.warning("All database tables dropped")
        except Exception as e:
            logger.error(f"Error dropping tables: {e}")
            raise


# Singleton instance
db_manager = DatabaseManager()


def init_database():
    """Initialize database and create tables"""
    try:
        db_manager.create_all_tables()
        logger.info("Database initialized successfully")
        return True
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        return False


def get_session() -> Generator[Session, None, None]:
    """
    Get database session (convenience function)
    
    Usage:
        with get_session() as session:
            tracks = session.query(Track).all()
    """
    return db_manager.get_session()
