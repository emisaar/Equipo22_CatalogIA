"""
Script to reset the database by dropping and recreating all tables.
Use this when you need to apply schema changes that require dropping tables.
"""
from sqlalchemy import text
from app.core.database import engine, Base
from app.models import user, product, order, wishlist
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def reset_database():
    """Drop all tables and recreate them."""
    try:
        with engine.connect() as conn:
            # Enable pgvector extension first
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            conn.commit()
            logger.info("pgvector extension enabled")

            # Drop all tables in reverse order (to handle foreign keys)
            logger.info("Dropping existing tables...")
            conn.execute(text("DROP TABLE IF EXISTS wishlist CASCADE"))
            conn.execute(text("DROP TABLE IF EXISTS orders CASCADE"))
            conn.execute(text("DROP TABLE IF EXISTS users CASCADE"))
            conn.execute(text("DROP TABLE IF EXISTS products CASCADE"))
            conn.commit()
            logger.info("All tables dropped successfully")

        # Recreate all tables using SQLAlchemy models
        logger.info("Creating tables with new schema...")
        Base.metadata.create_all(bind=engine)
        logger.info("All tables created successfully with Integer IDs")

    except Exception as e:
        logger.error(f"Error resetting database: {e}")
        raise


if __name__ == "__main__":
    print("WARNING: This will drop all existing data in the database!")
    print("Proceeding with database reset...")
    reset_database()
    print("\n✓ Database reset complete. All tables now use Integer IDs.")
