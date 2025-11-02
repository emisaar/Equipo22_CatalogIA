from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from app.api.v1 import router as api_router
from app.api import deps
from app.core.config import settings
from app.core.database import init_db
from app.services.embeddings import embedding_service
import logging

logger = logging.getLogger(__name__)

# Inicializar base de datos (pgvector + tablas)
init_db()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Gestiona el ciclo de vida de la aplicación.

    Startup: Se ejecuta cuando la aplicación inicia.
    Shutdown: Se ejecuta cuando la aplicación se detiene.
    """
    # Startup
    logger.info("Iniciando aplicación CatalogIA...")
    logger.info("Pre-cargando modelo de embeddings...")
    embedding_service.warmup()
    logger.info("Aplicación iniciada exitosamente")

    yield

    # Shutdown
    logger.info("Cerrando aplicación CatalogIA...")


app = FastAPI(
    title="CatalogIA API",
    description="FastAPI backend for CatalogIA platform with AI recommendations",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router.api_router, prefix="/api/v1")


@app.get("/")
def root():
    """
    Root endpoint
    """
    return {"message": "E-commerce API", "version": "1.0.0"}


@app.get("/health")
def health_check(db: Session = Depends(deps.get_db)):
    """
    Health check endpoint
    """
    try:
        db.execute("SELECT 1")
        db_status = "healthy"
    except Exception:
        db_status = "unhealthy"

    return {
        "status": "healthy" if db_status == "healthy" else "unhealthy",
        "database": db_status,
        "embeddings_model_loaded": embedding_service.is_model_loaded(),
        "environment": settings.ENVIRONMENT,
        "version": "1.0.0"
    }