from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.api import deps
from app.crud import product
from app.schemas.product import ProductCreate, ProductResponse, ProductUpdate, ProductList, SemanticSearchResult, ProductWithScore

router = APIRouter()


@router.post("/", response_model=ProductResponse, status_code=201)
def create_product(
    *,
    db: Session = Depends(deps.get_db),
    product_in: ProductCreate,
):
    """
    Crear un nuevo producto en el catálogo.

    Genera automáticamente el embedding semántico del producto.

    Args:
        - `db`: Sesión de base de datos 
        - `product_in`: Datos del producto a crear

    Returns:
        `ProductResponse`: Producto creado con todos sus datos

    Raises:
        `HTTPException`: 400 si ya existe un producto con el mismo EAN
    """
    existing_product = product.get_by_ean(db, ean=product_in.ean)
    if existing_product:
        raise HTTPException(
            status_code=400,
            detail="Ya existe un producto con este código EAN"
        )

    created_product = product.create(db, obj_in=product_in)
    return created_product


@router.get("/", response_model=ProductList)
def list_products(
    db: Session = Depends(deps.get_db),
    skip: int = Query(0, ge=0, description="Número de productos a saltar para paginación"),
    limit: int = Query(100, ge=1, le=1000, description="Límite de productos por página"),
    category: Optional[str] = Query(None, description="Filtrar por categoría"),
    min_price: Optional[float] = Query(None, ge=0, description="Precio mínimo"),
    max_price: Optional[float] = Query(None, ge=0, description="Precio máximo"),
):
    """
    Listar productos con filtros opcionales y paginación.

    Args:
        - `skip`: Número de productos a omitir (para paginación)
        - `limit`: Número máximo de productos a retornar
        - `category`: Filtro por categoría
        - `min_price`: Precio mínimo
        - `max_price`: Precio máximo

    Returns:
        `ProductList`: Lista paginada de productos con metadatos
    """
    products = product.get_by_filters(
        db=db,
        category=category,
        min_price=min_price,
        max_price=max_price,
        skip=skip,
        limit=limit
    )

    total = product.count_by_filters(
        db=db,
        category=category,
        min_price=min_price,
        max_price=max_price
    )

    return ProductList(
        products=products,
        total=total,
        skip=skip,
        limit=limit
    )


@router.get("/search/semantic", response_model=SemanticSearchResult)
def semantic_search_products(
    q: str = Query(..., min_length=1, description="Texto de búsqueda"),
    db: Session = Depends(deps.get_db),
    limit: int = Query(10, ge=1, le=100, description="Número de resultados"),
    category: Optional[str] = Query(None, description="Filtrar por categoría"),
    min_price: Optional[float] = Query(None, ge=0, description="Precio mínimo"),
    max_price: Optional[float] = Query(None, ge=0, description="Precio máximo"),
    min_similarity: float = Query(0.3, ge=0.0, le=1.0, description="Umbral mínimo de similitud (0-1)"),
):
    """
    Búsqueda semántica de productos usando IA.

    Esta búsqueda utiliza embeddings y similitud semántica para encontrar
    productos relevantes basándose en el SIGNIFICADO del texto, no solo
    en coincidencias exactas de palabras.

    Args:
        - `q`: Texto de búsqueda (ej: "laptop para trabajar desde casa")
        - `limit`: Número máximo de resultados a retornar
        - `category`: Filtro opcional por categoría
        - `min_price`: Precio mínimo del filtro
        - `max_price`: Precio máximo del filtro
        - `min_similarity`: Umbral mínimo de similitud (0.3 recomendado, 0.5 restrictivo)

    Returns:
        `SemanticSearchResult`: Productos ordenados por relevancia con scores de similitud
    """
    results = product.semantic_search(
        db=db,
        query_text=q,
        limit=limit,
        category=category,
        min_price=min_price,
        max_price=max_price,
        min_similarity=min_similarity
    )

    # Convertir resultados a ProductWithScore
    products_with_scores = [
        ProductWithScore(
            **product.__dict__,
            similarity_score=score
        )
        for product, score in results
    ]

    return SemanticSearchResult(
        products=products_with_scores,
        total=len(products_with_scores),
        skip=0,
        limit=limit,
        min_similarity=min_similarity
    )


@router.get("/{product_id}", response_model=ProductResponse)
def get_product(
    product_id: int,
    db: Session = Depends(deps.get_db),
):
    """
    Obtener un producto específico por su ID.

    Args:
        - `product_id`: ID del producto a buscar

    Returns:
        `ProductResponse`: Datos completos del producto

    Raises:
        `HTTPException`: 404 si el producto no existe
    """
    db_product = product.get(db, id=product_id)
    if not db_product:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    return db_product


@router.put("/{product_id}", response_model=ProductResponse)
def update_product(
    *,
    db: Session = Depends(deps.get_db),
    product_id: int,
    product_in: ProductUpdate
):
    """
    Actualizar un producto existente.

    Regenera automáticamente el embedding si se modifican campos relevantes
    (título, descripción, categoría, subcategoría, o características).

    Args:
        - `product_id`: ID del producto a actualizar
        - `product_in`: Datos a actualizar (solo campos presentes se modifican)

    Returns:
        `ProductResponse`: Producto actualizado

    Raises:
        `HTTPException`: 404 si el producto no existe
        `HTTPException`: 400 si el nuevo EAN ya está en uso
    """
    db_product = product.get(db, id=product_id)
    if not db_product:
        raise HTTPException(status_code=404, detail="Producto no encontrado")

    if product_in.ean and product_in.ean != db_product.ean:
        existing_product = product.get_by_ean(db, ean=product_in.ean)
        if existing_product:
            raise HTTPException(
                status_code=400,
                detail="Ya existe un producto con este código EAN"
            )

    updated_product = product.update(db, db_obj=db_product, obj_in=product_in)
    return updated_product


@router.delete("/{product_id}")
def delete_product(
    *,
    db: Session = Depends(deps.get_db),
    product_id: int
):
    """
    Eliminar un producto del catálogo.

    Args:
        - `product_id`: ID del producto a eliminar

    Returns:
        `dict`: Mensaje de confirmación

    Raises:
        `HTTPException`: 404 si el producto no existe
    """
    db_product = product.get(db, id=product_id)
    if not db_product:
        raise HTTPException(status_code=404, detail="Producto no encontrado")

    product.delete(db, id=product_id)
    return {"message": "Producto eliminado exitosamente"}
