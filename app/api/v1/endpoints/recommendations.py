from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.api import deps
from app.crud import product, wishlist, order
from app.schemas.product import RecommendationResult, ProductWithScore
from app.models.user import User

router = APIRouter()


@router.get("/personalized", response_model=RecommendationResult)
def get_personalized_recommendations(
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
    limit: int = Query(10, ge=1, le=100, description="Número de recomendaciones"),
    strategy: str = Query("semantic", description="Estrategia: 'semantic', 'category', 'hybrid'"),
    min_similarity: float = Query(0.0, ge=0.0, le=1.0, description="Umbral mínimo de similitud (0-1). 0=sin filtro, 0.3+=restrictivo"),
    exclude_purchased: bool = Query(False, description="Excluir productos ya comprados")
):
    """
    Obtener recomendaciones personalizadas basadas en el wishlist del usuario.

    Utiliza IA para analizar los productos en tu wishlist y recomendar productos similares.

    **Estrategias:**
    - `semantic`: Similitud semántica con embeddings de IA (recomendado)
    - `category`: Productos de tus categorías favoritas
    - `hybrid`: Combina ambas estrategias

    Args:
        - `limit`: Número máximo de recomendaciones (1-100)
        - `strategy`: Estrategia de recomendación
        - `min_similarity`: Umbral de similitud (0-1). 0=sin filtro, 0.3+=restrictivo
        - `exclude_purchased`: Excluir productos ya comprados

    Returns:
        Lista de productos recomendados con scores de similitud

    Notes:
        - Si wishlist está vacío, retorna productos populares
        - Scores: 0 a 1 (1 = más similar)
        - Requiere autenticación (JWT)
    """
    wishlist_items = wishlist.get_by_user(db, user_id=current_user.id)
    wishlist_products = [item.product for item in wishlist_items]

    purchased_product_ids = None
    if exclude_purchased:
        user_orders = order.get_by_user(db, user_id=current_user.id)
        purchased_product_ids = list(set([o.product_id for o in user_orders]))

    recommendations = product.get_personalized_recommendations(
        db=db,
        user_wishlist_products=wishlist_products,
        user_purchased_product_ids=purchased_product_ids,
        limit=limit,
        min_similarity=min_similarity,
        strategy=strategy
    )

    products_with_scores = [
        ProductWithScore(**prod.__dict__, similarity_score=score)
        for prod, score in recommendations
    ]

    return RecommendationResult(
        products=products_with_scores,
        total=len(products_with_scores),
        limit=limit,
        strategy=strategy,
        wishlist_size=len(wishlist_products),
        min_similarity=min_similarity if strategy in ["semantic", "hybrid"] else None
    )
