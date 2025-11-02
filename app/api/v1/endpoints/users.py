from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.api import deps
from app.crud import user
from app.schemas.user import UserCreate, UserLogin, UserResponse, UserUpdate, Token
from app.models.user import User
from app.core.security import create_access_token
from app.core.config import settings

router = APIRouter()


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(
    *,
    db: Session = Depends(deps.get_db),
    user_in: UserCreate,
):
    """
    Crear un nuevo usuario en el sistema.
    
    Args:
        `db`: Sesión de base de datos
        `user_in`: Datos del usuario a crear
    
    Returns:
        `UserResponse`: Usuario creado con todos sus datos
        
    Raises:
        `HTTPException`: 400 si ya existe un usuario con el mismo email o username
    """
    existing_user = user.get_by_email(db, email=user_in.email)
    if existing_user:
        raise HTTPException(
            status_code=400,
            detail="Ya existe un usuario con este email en el sistema.",
        )
    
    existing_username = user.get_by_username(db, username=user_in.username)
    if existing_username:
        raise HTTPException(
            status_code=400,
            detail="Ya existe un usuario con este nombre de usuario.",
        )
    
    created_user = user.create(db, obj_in=user_in)
    return created_user


@router.post("/login", response_model=Token)
def login_for_access_token(
    *,
    db: Session = Depends(deps.get_db),
    user_in: UserLogin,
):
    """
    Iniciar sesión y obtener token de acceso JWT.
    
    Args:
        `db`: Sesión de base de datos
        `user_in`: Credenciales de login (email y password)
    
    Returns:
        `Token`: Token de acceso JWT y tipo de token
        
    Raises:
        `HTTPException`: 401 si las credenciales son incorrectas
    """
    authenticated_user = user.authenticate(
        db, email=user_in.email, password=user_in.password
    )
    if not authenticated_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email o contraseña incorrectos",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": authenticated_user.email}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/me", response_model=UserResponse)
def read_user_me(
    current_user: User = Depends(deps.get_current_user),
):
    """
    Obtener información del usuario autenticado actual.
    
    Args:
        `current_user`: Usuario autenticado mediante token JWT
    
    Returns:
        `UserResponse`: Datos completos del usuario actual
    """
    return current_user


@router.get("/{user_id}", response_model=UserResponse)
def read_user(
    user_id: int,
    db: Session = Depends(deps.get_db),
):
    """
    Obtener un usuario específico por su ID.

    Args:
        `user_id`: ID del usuario a buscar
        `db`: Sesión de base de datos

    Returns:
        `UserResponse`: Datos completos del usuario

    Raises:
        `HTTPException`: 404 si el usuario no existe
    """
    db_user = user.get(db, id=user_id)
    if not db_user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return db_user


@router.put("/{user_id}", response_model=UserResponse)
def update_user(
    *,
    db: Session = Depends(deps.get_db),
    user_id: int,
    user_in: UserUpdate,
    current_user: User = Depends(deps.get_current_user),
):
    """
    Actualizar los datos de un usuario.

    Args:
        `db`: Sesión de base de datos
        `user_id`: ID del usuario a actualizar
        `user_in`: Datos del usuario a actualizar
        `current_user`: Usuario autenticado actual

    Returns:
        `UserResponse`: Usuario actualizado con los nuevos datos

    Raises:
        `HTTPException`: 404 si el usuario no existe
        `HTTPException`: 403 si no tienes permisos para actualizar el usuario
    """
    db_user = user.get(db, id=user_id)
    if not db_user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    if db_user.id != current_user.id:
        raise HTTPException(status_code=403, detail="No tienes permisos para realizar esta acción")

    updated_user = user.update(db, db_obj=db_user, obj_in=user_in)
    return updated_user


@router.delete("/{user_id}")
def delete_user(
    *,
    db: Session = Depends(deps.get_db),
    user_id: int,
    current_user: User = Depends(deps.get_current_user),
):
    """
    Eliminar un usuario del sistema.

    Args:
        `db`: Sesión de base de datos
        `user_id`: ID del usuario a eliminar
        `current_user`: Usuario autenticado actual

    Returns:
        `dict`: Mensaje de confirmación de eliminación

    Raises:
        `HTTPException`: 404 si el usuario no existe
        `HTTPException`: 403 si no tienes permisos para eliminar el usuario
    """
    db_user = user.get(db, id=user_id)
    if not db_user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    if db_user.id != current_user.id:
        raise HTTPException(status_code=403, detail="No tienes permisos para realizar esta acción")

    user.delete(db, id=user_id)
    return {"message": "Usuario eliminado exitosamente"}