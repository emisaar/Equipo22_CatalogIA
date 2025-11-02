from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.api import deps
from app.crud import wishlist, product
from app.schemas.wishlist import WishlistCreate, WishlistResponse, WishlistList
from app.models.user import User

router = APIRouter()


@router.post("/", response_model=WishlistResponse, status_code=201)
def add_to_wishlist(
    *,
    db: Session = Depends(deps.get_db),
    wishlist_in: WishlistCreate,
    current_user: User = Depends(deps.get_current_user),
):
    """
    Agregar un producto a la lista de deseos del usuario.
    
    Args:
        `db`: Sesión de base de datos
        `wishlist_in`: Datos del producto a agregar
        `current_user`: Usuario autenticado actual
    
    Returns:
        `WishlistResponse`: Item agregado a la wishlist
        
    Raises:
        `HTTPException`: 404 si el producto no existe
        `HTTPException`: 400 si el producto ya está en la wishlist
    """
    db_product = product.get(db, id=wishlist_in.product_id)
    if not db_product:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    
    existing_item = wishlist.check_exists(
        db, user_id=current_user.id, product_id=wishlist_in.product_id
    )
    if existing_item:
        raise HTTPException(
            status_code=400,
            detail="El producto ya está en tu lista de deseos"
        )
    
    wishlist_item = wishlist.create_user_wishlist(
        db, user_id=current_user.id, product_id=wishlist_in.product_id
    )
    return wishlist_item


@router.get("/", response_model=WishlistList)
def get_user_wishlist(
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
):
    """
    Obtener la lista de deseos completa del usuario autenticado.
    
    Args:
        `db`: Sesión de base de datos
        `current_user`: Usuario autenticado actual
    
    Returns:
        `WishlistList`: Lista completa de productos en la wishlist con detalles del producto
    """
    wishlist_items = wishlist.get_by_user(db, user_id=current_user.id)
    total = wishlist.count_by_user(db, user_id=current_user.id)
    
    return WishlistList(
        items=wishlist_items,
        total=total
    )


@router.delete("/{product_id}")
def remove_from_wishlist(
    *,
    db: Session = Depends(deps.get_db),
    product_id: str,
    current_user: User = Depends(deps.get_current_user),
):
    """
    Eliminar un producto de la lista de deseos del usuario.
    
    Args:
        `db`: Sesión de base de datos
        `product_id`: UUID del producto a eliminar de la wishlist
        `current_user`: Usuario autenticado actual
    
    Returns:
        `dict`: Mensaje de confirmación de eliminación
        
    Raises:
        `HTTPException`: 404 si el producto no está en la wishlist
    """
    success = wishlist.remove_from_wishlist(
        db, user_id=current_user.id, product_id=product_id
    )
    
    if not success:
        raise HTTPException(
            status_code=404,
            detail="El producto no está en tu lista de deseos"
        )
    
    return {"message": "Producto eliminado de la lista de deseos"}


@router.get("/check/{product_id}")
def check_product_in_wishlist(
    product_id: str,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
):
    """
    Verificar si un producto específico está en la lista de deseos del usuario.

    Args:
        `product_id`: UUID del producto a verificar
        `db`: Sesión de base de datos
        `current_user`: Usuario autenticado actual
    
    Returns:
        `dict`: Indicador booleano de si el producto está en la wishlist
    """
    exists = wishlist.check_exists(
        db, user_id=current_user.id, product_id=product_id
    )
    
    return {"in_wishlist": exists is not None}