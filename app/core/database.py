from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

engine = create_engine(settings.DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def init_db():
    """
    Inicializa la base de datos:
    - Habilita la extensión pgvector
    - Crea todas las tablas
    """
    try:
        with engine.connect() as conn:
            # Habilitar extensión pgvector
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            conn.commit()
            logger.info("Extensión pgvector habilitada")
    except Exception as e:
        logger.error(f"Error habilitando extensión pgvector: {e}")
        raise

    # Crear todas las tablas
    Base.metadata.create_all(bind=engine)
    logger.info("Tablas de base de datos creadas")