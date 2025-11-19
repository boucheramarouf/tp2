from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from typing import List
import logging
from datetime import timedelta

from .crud import (
    get_movies, get_movie, create_movie, update_movie, delete_movie,
    get_user_by_email, create_user, authenticate_user, create_access_token, ACCESS_TOKEN_EXPIRE_MINUTES
)
from .dependencies import get_db, get_current_user, get_current_admin
from .schema import Movie, MovieCreate, MovieUpdate, VALID_GENRES, UserRegister, UserLogin, Token
from .models import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/movies", tags=["Movies"])
auth_router = APIRouter(prefix="/auth", tags=["Authentication"])
admin_router = APIRouter(prefix="/admin", tags=["Admin"])

# Routes d'authentification
@auth_router.post("/register", status_code=status.HTTP_201_CREATED)
def register(user_data: UserRegister, db: Session = Depends(get_db)):
    user = create_user(db, user_data.model_dump())
    return {
        "message": "Utilisateur créé avec succès",
        "email": user.email,
        "role": user.role
    }

@auth_router.post("/login", response_model=Token)
def login(user_data: UserLogin, db: Session = Depends(get_db)):
    user = authenticate_user(db, user_data.email, user_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou mot de passe incorrect",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email, "role": user.role},
        expires_delta=access_token_expires
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer"
    }

# Routes Admin
@admin_router.get("/users")
def get_all_users(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_admin)
):
    users = db.query(User).all()
    return {
        "users": [
            {
                "id": user.id,
                "email": user.email,
                "role": user.role
            }
            for user in users
        ]
    }

@admin_router.post("/create-admin")
def create_admin_user(
    user_data: UserRegister,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_admin)
):
    admin_data = user_data.model_dump()
    admin_data["role"] = "admin"
    
    user = create_user(db, admin_data)
    return {
        "message": "Administrateur créé avec succès",
        "email": user.email,
        "role": user.role
    }

# Routes Movies protégées
@router.get("/", response_model=List[Movie])
def list_movies(
    title: str | None = None,
    genre: str | None = None,
    studio: str | None = None,
    year_min: int | None = None,
    year_max: int | None = None,
    min_profitability: float | None = None,
    order_by: str | None = Query(None, description="Tri (ex: audience_score, -worldwide_gross)"),
    page: int = Query(1, ge=1, description="Numéro de page"),
    limit: int = Query(10, ge=1, le=100, description="Nombre d'éléments par page"),
    sort_by: str = Query("id", description="Champ de tri: title, year, audience_score, etc."),
    order: str = Query("asc", description="Ordre de tri: asc ou desc"),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    try:
        filters = {
            "title": title,
            "genre": genre,
            "studio": studio,
            "year_min": year_min,
            "year_max": year_max,
            "min_profitability": min_profitability,
            "order_by": order_by,
            "page": page,
            "limit": limit,
            "sort_by": sort_by,
            "order": order
        }
        
        filters = {k: v for k, v in filters.items() if v is not None}
        movies = get_movies(db, filters) 
        return movies
    
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des films: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur interne du serveur lors de la récupération des films"
        )

@router.get("/{movie_id}", response_model=Movie)
def get_one_movie(
    movie_id: int, 
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    if movie_id <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="L'ID du film doit être un nombre positif"
        )
    
    movie = get_movie(db, movie_id)
    if not movie:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Film avec l'ID {movie_id} introuvable"
        )
    return movie

@router.post("/", response_model=Movie, status_code=status.HTTP_201_CREATED)
def create_new_movie(
    data: MovieCreate, 
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    try:   
        current_year = 2024  
        if data.year >= current_year - 2 and data.audience_score == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Les films récents (moins de 2 ans) doivent avoir un score audience"
            )
        
        return create_movie(db, data.model_dump())
    
    except ValueError as e:
        if "existe déjà" in str(e):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=str(e)
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )
    
    except Exception as e:
        logger.error(f"Erreur inattendue lors de la création: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur interne du serveur lors de la création du film"
        )

@router.put("/{movie_id}", response_model=Movie)
def update_one_movie_put(
    movie_id: int, 
    data: MovieCreate, 
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    existing_movie = get_movie(db, movie_id)
    if not existing_movie:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Film avec l'ID {movie_id} introuvable - impossible de mettre à jour"
        )
    
    try:
        current_year = 2024
        if data.year >= current_year - 2 and data.audience_score == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Les films récents (moins de 2 ans) doivent avoir un score audience"
            )
        
        delete_movie(db, movie_id)
        return create_movie(db, data.model_dump())
    
    except ValueError as e:
        if "existe déjà" in str(e):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=str(e)
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )

@router.patch("/{movie_id}", response_model=Movie)
def update_one_movie(
    movie_id: int, 
    data: MovieUpdate, 
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    existing_movie = get_movie(db, movie_id)
    if not existing_movie:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Film avec l'ID {movie_id} introuvable - impossible de mettre à jour"
        )
    
    try:
        update_data = data.model_dump(exclude_unset=True)
        
        current_year = 2024
        year = update_data.get('year', existing_movie.year)
        audience_score = update_data.get('audience_score', existing_movie.audience_score)
        
        if year >= current_year - 2 and audience_score == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Les films récents (moins de 2 ans) doivent avoir un score audience"
            )
        
        if 'genre' in update_data:
            normalized_genre = update_data['genre'].strip().title()
            if normalized_genre not in VALID_GENRES:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Genre '{update_data['genre']}' non autorisé. Genres valides: {', '.join(VALID_GENRES)}"
                )
        
        movie = update_movie(db, movie_id, update_data)
        return movie
    
    except ValueError as e:
        if "existe déjà" in str(e):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=str(e)
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )
    
    except Exception as e:
        logger.error(f"Erreur lors de la mise à jour du film {movie_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur interne du serveur lors de la mise à jour du film"
        )

@router.delete("/{movie_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_movie(
    movie_id: int, 
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    if movie_id <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="L'ID du film doit être un nombre positif"
        )
    
    existing_movie = get_movie(db, movie_id)
    if not existing_movie:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Film avec l'ID {movie_id} introuvable - impossible de supprimer"
        )
    
    try:
        success = delete_movie(db, movie_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Film avec l'ID {movie_id} introuvable"
            )
        
    except Exception as e:
        logger.error(f"Erreur lors de la suppression du film {movie_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur interne du serveur lors de la suppression du film"
        )