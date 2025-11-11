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
        min_similarity: float = 0.15
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
            min_similarity: Umbral mínimo de similitud (0-1).

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

            # Generar embedding de la búsqueda (con prefijo retrieval_query)
            query_embedding = embedding_service.generate_embedding(processed_query, is_query=True)

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

    def get_personalized_recommendations(
        self,
        db: Session,
        *,
        user_wishlist_products: List[Product],
        user_purchased_product_ids: List[int] = None,
        limit: int = 10,
        min_similarity: float = 0.0,
        strategy: str = "semantic"
    ) -> List[Tuple[Product, float]]:
        """
        Genera recomendaciones personalizadas basadas en el wishlist del usuario.

        Args:
            db: Sesión de base de datos
            user_wishlist_products: Lista de productos en el wishlist del usuario
            user_purchased_product_ids: IDs de productos ya comprados (para excluir)
            limit: Número máximo de recomendaciones
            min_similarity: Umbral mínimo de similitud (0-1)
            strategy: Estrategia ("semantic", "category", "hybrid")

        Returns:
            Lista de tuplas (producto, similarity_score) ordenadas por relevancia
        """
        try:
            if not user_wishlist_products:
                logger.info("Wishlist vacío, retornando productos populares")
                return self._get_popular_products(db, limit=limit)

            exclude_ids = [p.id for p in user_wishlist_products]
            if user_purchased_product_ids:
                exclude_ids.extend(user_purchased_product_ids)

            logger.info(f"Generando recomendaciones con estrategia '{strategy}' para {len(user_wishlist_products)} productos en wishlist")

            if strategy == "semantic" or strategy == "hybrid":
                return self._recommend_by_semantic_similarity(
                    db=db,
                    wishlist_products=user_wishlist_products,
                    exclude_ids=exclude_ids,
                    limit=limit,
                    min_similarity=min_similarity
                )
            elif strategy == "category":
                return self._recommend_by_category(
                    db=db,
                    wishlist_products=user_wishlist_products,
                    exclude_ids=exclude_ids,
                    limit=limit
                )
            else:
                logger.warning(f"Estrategia desconocida '{strategy}', usando 'semantic'")
                return self._recommend_by_semantic_similarity(
                    db=db,
                    wishlist_products=user_wishlist_products,
                    exclude_ids=exclude_ids,
                    limit=limit,
                    min_similarity=min_similarity
                )

        except Exception as e:
            logger.error(f"Error en recomendaciones personalizadas: {str(e)}", exc_info=True)
            return []

    def _recommend_by_semantic_similarity(
        self,
        db: Session,
        wishlist_products: List[Product],
        exclude_ids: List[int],
        limit: int,
        min_similarity: float
    ) -> List[Tuple[Product, float]]:
        """
        Recomendaciones basadas en similitud semántica con el embedding promedio del wishlist.
        """
        embeddings = [p.product_embedding for p in wishlist_products if p.product_embedding is not None]

        if not embeddings:
            logger.warning("No hay embeddings en los productos del wishlist")
            return []

        logger.info(f"Calculando recomendaciones desde {len(embeddings)} productos en wishlist")

        # Calcular centroide (promedio) de los embeddings
        avg_embedding = [sum(dim) / len(embeddings) for dim in zip(*embeddings)]

        # Buscar productos similares al centroide
        similarity_expr = (1 - Product.product_embedding.cosine_distance(avg_embedding))

        total_available = db.query(func.count(Product.id)).filter(
            Product.product_embedding.isnot(None),
            ~Product.id.in_(exclude_ids)
        ).scalar()

        query = db.query(
            Product,
            similarity_expr.label('similarity')
        ).filter(
            Product.product_embedding.isnot(None),
            ~Product.id.in_(exclude_ids)
        )

        # Aplicar umbral de similitud (reducir automáticamente para datasets pequeños)
        effective_threshold = min_similarity
        if total_available < 20 and min_similarity > 0:
            effective_threshold = max(0.05, min_similarity * 0.5)
            logger.info(f"Dataset pequeño detectado, reduciendo umbral de {min_similarity} a {effective_threshold}")

        if effective_threshold > 0:
            query = query.filter(similarity_expr >= effective_threshold)

        results = query.order_by(similarity_expr.desc()).limit(limit).all()

        if results:
            similarities = [float(sim) for _, sim in results]
            logger.info(f"Recomendaciones semánticas: {len(results)} productos encontrados")
            logger.info(f"Rango de similitud: {min(similarities):.3f} - {max(similarities):.3f}")
        else:
            logger.warning(f"No se encontraron recomendaciones semánticas con threshold {effective_threshold}")
            # Intentar sin threshold como último recurso
            if effective_threshold > 0:
                logger.info("Intentando sin threshold...")
                query_no_threshold = db.query(
                    Product,
                    similarity_expr.label('similarity')
                ).filter(
                    Product.product_embedding.isnot(None),
                    ~Product.id.in_(exclude_ids)
                )
                results = query_no_threshold.order_by(similarity_expr.desc()).limit(limit).all()
                if results:
                    similarities = [float(sim) for _, sim in results]
                    logger.info(f"Encontrados {len(results)} productos sin threshold. Similitud: {min(similarities):.3f} - {max(similarities):.3f}")

        return [(product, float(similarity)) for product, similarity in results]

    def _recommend_by_category(
        self,
        db: Session,
        wishlist_products: List[Product],
        exclude_ids: List[int],
        limit: int
    ) -> List[Tuple[Product, float]]:
        """
        Recomendaciones basadas en las categorías más frecuentes del wishlist.
        """
        from collections import Counter

        categories = [p.category for p in wishlist_products if p.category]
        if not categories:
            return []

        category_counts = Counter(categories)
        most_common_category = category_counts.most_common(1)[0][0]

        logger.info(f"Categoría más común en wishlist: {most_common_category}")

        # Normalizar rating (0-5) a score (0-1)
        normalized_score = (Product.rating / 5.0).label('score')

        results = db.query(
            Product,
            normalized_score
        ).filter(
            Product.category == most_common_category,
            ~Product.id.in_(exclude_ids)
        ).order_by(Product.rating.desc()).limit(limit).all()

        logger.info(f"Recomendaciones por categoría: {len(results)} productos encontrados")
        return [(product, float(score)) for product, score in results]

    def _get_popular_products(
        self,
        db: Session,
        limit: int
    ) -> List[Tuple[Product, float]]:
        """
        Retorna productos populares como fallback cuando el wishlist está vacío.
        Usa rating como criterio de popularidad.
        """
        normalized_score = (Product.rating / 5.0).label('score')

        results = db.query(
            Product,
            normalized_score
        ).order_by(Product.rating.desc()).limit(limit).all()

        logger.info(f"Productos populares (fallback): {len(results)} productos encontrados")
        return [(product, float(score)) for product, score in results]


product = CRUDProduct(Product)