from sqlalchemy import and_, asc, desc
from sqlalchemy.orm import Session
from .models import Movie, User
from werkzeug.security import generate_password_hash, check_password_hash
from jose import JWTError, jwt
from datetime import datetime, timedelta
from fastapi import HTTPException, status

# Configuration
SECRET_KEY = "votre_cle_secrete_super_securisee_changez_moi"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Fonctions pour les films (existantes)
def get_movies(session: Session, filters: dict):
    query = session.query(Movie)

    if not filters:
        filters = {}
    if "title" in filters:
        query = query.filter(Movie.title.ilike(f"%{filters['title']}%"))

    if "genre" in filters and hasattr(Movie, "genre"):
        query = query.filter(Movie.genre.ilike(f"%{filters['genre']}%"))

    if "studio" in filters and hasattr(Movie, "studio"):
        query = query.filter(Movie.studio.ilike(f"%{filters['studio']}%"))

    if "year_min" in filters:
        query = query.filter(Movie.year >= filters["year_min"])

    if "year_max" in filters:
        query = query.filter(Movie.year <= filters["year_max"])

    if "min_profitability" in filters and hasattr(Movie, "profitability"):
        query = query.filter(Movie.profitability >= filters["min_profitability"])

    order = filters.get("order_by")
    if order:
        desc_mode = order.startswith("-")
        field_name = order.lstrip('-')

        if hasattr(Movie, field_name):
            field = getattr(Movie, field_name)
            query = query.order_by(desc(field) if desc_mode else asc(field))

    if "page" in filters and "limit" in filters:
        page = filters["page"]
        limit = filters["limit"]
        offset = (page - 1) * limit
        query = query.offset(offset).limit(limit)
    
    return query.all()

def get_movie(session: Session, movie_id: int):
    return session.query(Movie).filter(Movie.id == movie_id).first()

def create_movie(session: Session, movie_data: dict):
    title = movie_data.get("title")
    year = movie_data.get("year")

    if not title or not year:
        raise ValueError("title et year sont obligatoires")

    exists = session.query(Movie).filter(
        Movie.title == title,
        Movie.year == year
    ).first()

    if exists:
        raise ValueError("Un film avec le même title+year existe déjà")

    movie = Movie(**movie_data)
    session.add(movie)
    session.commit()
    session.refresh(movie)

    return movie

def update_movie(session: Session, movie_id: int, movie_data: dict):
    movie = session.query(Movie).filter(Movie.id == movie_id).first()
    if not movie:
        return None

    for field, value in movie_data.items():
        if hasattr(movie, field):
            setattr(movie, field, value)

    session.commit()
    session.refresh(movie)

    return movie

def delete_movie(session: Session, movie_id: int):
    movie = session.query(Movie).filter(Movie.id == movie_id).first()
    if not movie:
        return False

    session.delete(movie)
    session.commit()
    return True

# NOUVELLES Fonctions pour l'authentification (avec werkzeug)
def get_user_by_email(db: Session, email: str):
    return db.query(User).filter(User.email == email).first()

def create_user(db: Session, user_data: dict):
    existing_user = get_user_by_email(db, user_data["email"])
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Un utilisateur avec cet email existe déjà"
        )
    
    # Utilisation de werkzeug pour hasher le mot de passe
    hashed_password = generate_password_hash(user_data["password"])
    
    user = User(
        email=user_data["email"],
        password=hashed_password,
        role=user_data.get("role", "user")
    )
    
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

def authenticate_user(db: Session, email: str, password: str):
    user = get_user_by_email(db, email)
    if not user:
        return False
    # Utilisation de werkzeug pour vérifier le mot de passe
    if not check_password_hash(user.password, password):
        return False
    return user

def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt