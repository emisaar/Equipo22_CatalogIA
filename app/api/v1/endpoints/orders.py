from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.api import deps
from app.crud import order, product
from app.schemas.order import OrderCreate, OrderResponse, OrderStatusUpdate, OrderList
from app.models.user import User

router = APIRouter()


@router.post("/", response_model=OrderResponse, status_code=201)
def create_order(
    *,
    db: Session = Depends(deps.get_db),
    order_in: OrderCreate,
    current_user: User = Depends(deps.get_current_user),
):
    """
    Crear una nueva orden de compra.
    
    Args:
        `db`: Sesión de base de datos
        `order_in`: Datos de la orden a crear
        `current_user`: Usuario autenticado que realiza la orden
    
    Returns:
        `OrderResponse`: Orden creada con el total calculado
        
    Raises:
        `HTTPException`: 404 si el producto no existe
        `HTTPException`: 400 si no hay suficiente stock
    """
    db_product = product.get(db, id=order_in.product_id)
    if not db_product:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    
    if db_product.stock < order_in.quantity:
        raise HTTPException(
            status_code=400,
            detail=f"Stock insuficiente. Disponible: {db_product.stock}"
        )
    
    unit_price = float(db_product.price * (1 - db_product.discount / 100))
    created_order = order.create_with_total(
        db, obj_in=order_in, user_id=current_user.id, unit_price=unit_price
    )
    
    db_product.stock -= order_in.quantity
    db.commit()
    
    return created_order


@router.get("/", response_model=OrderList)
def list_user_orders(
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
    skip: int = Query(0, ge=0, description="Número de órdenes a saltar para paginación"),
    limit: int = Query(100, ge=1, le=1000, description="Límite de órdenes por página"),
):
    """
    Obtener todas las órdenes del usuario autenticado.

    Args:
        `db`: Sesión de base de datos
        `current_user`: Usuario autenticado actual
        `skip`: Número de órdenes a omitir (para paginación)
        `limit`: Número máximo de órdenes a retornar
    
    Returns:
        `OrderList`: Lista paginada de órdenes del usuario
    """
    orders = order.get_by_user(db, user_id=current_user.id, skip=skip, limit=limit)
    total = order.count_by_user(db, user_id=current_user.id)
    
    return OrderList(
        orders=orders,
        total=total,
        skip=skip,
        limit=limit
    )


@router.get("/{order_id}", response_model=OrderResponse)
def get_order(
    order_id: str,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
):
    """
    Obtener una orden específica por su ID.
    
    Args:
        `order_id`: UUID de la orden a buscar
        `db`: Sesión de base de datos
        `current_user`: Usuario autenticado actual
    
    Returns:
        `OrderResponse`: Datos completos de la orden
        
    Raises:
        `HTTPException`: 404 si la orden no existe
        `HTTPException`: 403 si la orden no pertenece al usuario
    """
    db_order = order.get(db, id=order_id)
    if not db_order:
        raise HTTPException(status_code=404, detail="Orden no encontrada")
    
    if db_order.user_id != current_user.id:
        raise HTTPException(
            status_code=403, 
            detail="No tienes permisos para ver esta orden"
        )
    
    return db_order


@router.put("/{order_id}/status", response_model=OrderResponse)
def update_order_status(
    *,
    db: Session = Depends(deps.get_db),
    order_id: str,
    status_update: OrderStatusUpdate,
    current_user: User = Depends(deps.get_current_user),
):
    """
    Actualizar el estado de una orden.
    
    Args:
        `db`: Sesión de base de datos
        `order_id`: UUID de la orden a actualizar
        `status_update`: Nuevo estado de la orden
        `current_user`: Usuario autenticado actual
    
    Returns:
        `OrderResponse`: Orden con el estado actualizado
        
    Raises:
        `HTTPException`: 404 si la orden no existe
        `HTTPException`: 403 si la orden no pertenece al usuario
        `HTTPException`: 400 si el estado es inválido
    """
    db_order = order.get(db, id=order_id)
    if not db_order:
        raise HTTPException(status_code=404, detail="Orden no encontrada")
    
    if db_order.user_id != current_user.id:
        raise HTTPException(
            status_code=403, 
            detail="No tienes permisos para modificar esta orden"
        )
    
    if db_order.status == "completed" and status_update.status != "completed":
        raise HTTPException(
            status_code=400,
            detail="No se puede cambiar el estado de una orden completada"
        )
    
    updated_order = order.update_status(db, order_id=order_id, status=status_update.status)
    return updated_order


@router.delete("/{order_id}")
def cancel_order(
    *,
    db: Session = Depends(deps.get_db),
    order_id: str,
    current_user: User = Depends(deps.get_current_user),
):
    """
    Cancelar una orden (cambiar estado a 'cancelled').
    
    Args:
        `db`: Sesión de base de datos
        `order_id`: UUID de la orden a cancelar
        `current_user`: Usuario autenticado actual
    
    Returns:
        `dict`: Mensaje de confirmación de cancelación
        
    Raises:
        `HTTPException`: 404 si la orden no existe
        `HTTPException`: 403 si la orden no pertenece al usuario
        `HTTPException`: 400 si la orden ya está completada
    """
    db_order = order.get(db, id=order_id)
    if not db_order:
        raise HTTPException(status_code=404, detail="Orden no encontrada")
    
    if db_order.user_id != current_user.id:
        raise HTTPException(
            status_code=403, 
            detail="No tienes permisos para cancelar esta orden"
        )
    
    if db_order.status == "completed":
        raise HTTPException(
            status_code=400,
            detail="No se puede cancelar una orden completada"
        )
    
    if db_order.status != "cancelled":
        order.update_status(db, order_id=order_id, status="cancelled")
        
        db_product = product.get(db, id=db_order.product_id)
        if db_product:
            db_product.stock += db_order.quantity
            db.commit()
    
    return {"message": "Orden cancelada exitosamente"}