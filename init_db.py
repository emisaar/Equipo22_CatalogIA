"""
Script para inicializar la base de datos y crear todas las tablas.
"""
from sqlalchemy import text
from app.core.database import engine, Base


def init_db():
    """
    Crea todas las tablas en la base de datos.
    """
    print("Habilitando extensión pgvector...")
    with engine.connect() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        conn.commit()
    print("Extensión pgvector habilitada.")

    print("Creando tablas en la base de datos...")
    Base.metadata.create_all(bind=engine)
    print("Tablas creadas exitosamente.")

    print("Creando índice pgvector para búsqueda semántica...")
    with engine.connect() as conn:
        # Crear índice IVFFlat para optimizar búsquedas por similitud de coseno
        # lists=100 es apropiado para datasets de ~10K-100K productos
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_product_embedding_cosine
            ON products USING ivfflat (product_embedding vector_cosine_ops)
            WITH (lists = 100)
        """))
        conn.commit()
    print("Índice pgvector creado exitosamente.")


if __name__ == "__main__":
    init_db()
