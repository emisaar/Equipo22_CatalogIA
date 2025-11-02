from typing import List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.crud.base import CRUDBase
from app.models.product import Product
from app.schemas.product import ProductCreate, ProductUpdate
from app.services.embeddings import embedding_service
import logging

logger = logging.getLogger(__name__)


class CRUDProduct(CRUDBase[Product, ProductCreate, ProductUpdate]):
    def create(self, db: Session, *, obj_in: ProductCreate) -> Product:
        """
        Crea un nuevo producto y genera su embedding automáticamente.
        """
        # Generar embedding del producto
        embedding = embedding_service.generate_product_embedding(
            title=obj_in.title,
            description=obj_in.product_description,
            category=obj_in.category,
            brand=obj_in.brand,
            color=obj_in.color
        )

        # Crear objeto Product con el embedding
        db_obj = Product(
            **obj_in.model_dump(),
            product_embedding=embedding
        )
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def update(
        self, db: Session, *, db_obj: Product, obj_in: ProductUpdate
    ) -> Product:
        """
        Actualiza un producto y regenera su embedding si cambió información relevante.
        """
        update_data = obj_in.model_dump(exclude_unset=True)

        # Verificar si cambió algún campo que afecte el embedding
        embedding_fields = ['title', 'product_description', 'category', 'brand', 'color']
        needs_new_embedding = any(field in update_data for field in embedding_fields)

        if needs_new_embedding:
            # Regenerar embedding con los datos actualizados
            embedding = embedding_service.generate_product_embedding(
                title=update_data.get('title', db_obj.title),
                description=update_data.get('product_description', db_obj.product_description),
                category=update_data.get('category', db_obj.category),
                brand=update_data.get('brand', db_obj.brand),
                color=update_data.get('color', db_obj.color)
            )
            update_data['product_embedding'] = embedding

        # Actualizar campos
        for field, value in update_data.items():
            setattr(db_obj, field, value)

        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def get_by_ean(self, db: Session, *, ean: str) -> Optional[Product]:
        """
        Busca un producto por su código EAN.

        Usado para validar duplicados al crear productos.
        """
        return db.query(Product).filter(Product.ean == ean).first()

    def get_by_filters(
        self,
        db: Session,
        *,
        category: Optional[str] = None,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[Product]:
        query = db.query(Product)

        if category:
            query = query.filter(Product.category == category)
        if min_price is not None:
            query = query.filter(Product.price >= min_price)
        if max_price is not None:
            query = query.filter(Product.price <= max_price)

        return query.offset(skip).limit(limit).all()

    def count_by_filters(
        self,
        db: Session,
        *,
        category: Optional[str] = None,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None
    ) -> int:
        query = db.query(func.count(Product.id))

        if category:
            query = query.filter(Product.category == category)
        if min_price is not None:
            query = query.filter(Product.price >= min_price)
        if max_price is not None:
            query = query.filter(Product.price <= max_price)

        return query.scalar()

    def _preprocess_query(self, query_text: str) -> str:
        """
        Preprocesa el texto de búsqueda para mejorar la calidad de los embeddings.

        Args:
            query_text: Texto de búsqueda original

        Returns:
            Texto preprocesado
        """
        if not query_text:
            return ""

        # Normalizar espacios en blanco
        processed = " ".join(query_text.strip().split())

        # Convertir a minúsculas para consistencia
        processed = processed.lower()

        return processed

    def semantic_search(
        self,
        db: Session,
        *,
        query_text: str,
        limit: int = 10,
        category: Optional[str] = None,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
        min_similarity: float = 0.3
    ) -> List[Tuple[Product, float]]:
        """
        Búsqueda semántica de productos usando embeddings y similitud de coseno.

        Args:
            db: Sesión de base de datos
            query_text: Texto de búsqueda del usuario
            limit: Número máximo de resultados
            category: Filtro opcional por categoría
            min_price: Precio mínimo opcional
            max_price: Precio máximo opcional
            min_similarity: Umbral mínimo de similitud (0-1). Valores recomendados:
                          - 0.5-0.7: Muy restrictivo, solo resultados muy similares
                          - 0.3-0.5: Balanceado (recomendado)
                          - 0.1-0.3: Permisivo, más resultados pero menos relevantes

        Returns:
            Lista de tuplas (producto, similarity_score) ordenadas por similitud
            donde similarity_score está entre 0 y 1 (1 = idéntico, 0 = totalmente diferente)
        """
        try:
            # Validar query text
            if not query_text or not query_text.strip():
                logger.warning("Búsqueda semántica con query vacío")
                return []

            # Preprocesar query
            processed_query = self._preprocess_query(query_text)
            logger.info(f"Búsqueda semántica: '{query_text}' -> '{processed_query}'")

            # Generar embedding de la búsqueda
            query_embedding = embedding_service.generate_embedding(processed_query)

            # Construir query base con distancia de coseno
            # Usamos (1 - cosine_distance) para obtener similitud en vez de distancia
            similarity_expr = (1 - Product.product_embedding.cosine_distance(query_embedding))

            query = db.query(
                Product,
                similarity_expr.label('similarity')
            ).filter(
                Product.product_embedding.isnot(None)
            )

            # Aplicar umbral de similitud
            if min_similarity > 0:
                query = query.filter(similarity_expr >= min_similarity)

            # Aplicar filtros opcionales
            if category:
                query = query.filter(Product.category == category)
            if min_price is not None:
                query = query.filter(Product.price >= min_price)
            if max_price is not None:
                query = query.filter(Product.price <= max_price)

            # Ordenar por similitud (descendente - más similar primero)
            query = query.order_by(similarity_expr.desc())

            # Ejecutar query y retornar resultados
            results = query.limit(limit).all()

            logger.info(f"Búsqueda semántica retornó {len(results)} resultados")

            # Retornar lista de tuplas (producto, score)
            return [(product, float(similarity)) for product, similarity in results]

        except Exception as e:
            logger.error(f"Error en búsqueda semántica: {str(e)}", exc_info=True)
            # En caso de error, retornar lista vacía en lugar de fallar
            return []


product = CRUDProduct(Product)