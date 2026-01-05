"""
Database connection manager
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import NullPool
from contextlib import contextmanager
from typing import Generator
from pathlib import Path
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
        # Engine is lazy-loaded via get_engine property
        pass


    @property
    def get_engine(self):
        """Get SQLAlchemy engine, initializing it if not already done."""
        if self._engine is None:
            db_config = config.database
            db_type = db_config.get('type', 'postgresql')
            
            if db_type == 'sqlite':
                db_path = Path(__file__).parent.parent.parent / db_config.get('name', 'tonemix.db')
                url = f"sqlite:///{db_path}"
                self._engine = create_engine(url, echo=False)
                logger.info(f"SQLite engine created at {db_path}")
            else: # Default to PostgreSQL
                user = db_config.get('user', 'postgres')
                password = db_config.get('password', '')
                host = db_config.get('host', 'localhost')
                port = db_config.get('port', 5432)
                name = db_config.get('name', 'tonemix')
                
                url = (
                    f"postgresql://{user}:{password}"
                    f"@{host}:{port}/{name}"
                )
                self._engine = create_engine(
                    url,
                    echo=False,  # Set to True for SQL debugging
                    pool_pre_ping=True,  # Verify connections before using
                    pool_size=10,
                    max_overflow=20,
                )
                logger.info(f"PostgreSQL engine created for {host}:{port}/{name}")
            
            # Initialize session factory once engine is created
            self._session_factory = sessionmaker(bind=self._engine)
                
        return self._engine
    
    @contextmanager
    def get_session(self) -> Generator[Session, None, None]:
        """
        Context manager for database sessions
        
        Usage:
            with db_manager.get_session() as session:
                track = session.query(Track).first()
        """
        # Ensure engine and session_factory are initialized before getting a session
        if self._engine is None:
            _ = self.get_engine # Accessing the property will initialize _engine and _session_factory
        elif self._session_factory is None:
            self._session_factory = sessionmaker(bind=self._engine)

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
            Base.metadata.create_all(self.get_engine)
            logger.info("All database tables created successfully")
        except Exception as e:
            logger.error(f"Error creating tables: {e}")
            raise
    
    def drop_all_tables(self):
        """Drop all tables (use with caution!)"""
        try:
            Base.metadata.drop_all(self.get_engine)
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
