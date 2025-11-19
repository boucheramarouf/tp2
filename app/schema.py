from pydantic import BaseModel, Field, field_validator, EmailStr
from typing import Optional
from datetime import datetime

# Schémas Movies (existants)
VALID_GENRES = ["Action", "Drama", "Comedy", "Sci-Fi", "Romance", "Fantasy", "Animation", "Horror", "Thriller"]

class MovieBase(BaseModel):
    title: str = Field(..., min_length=2, max_length=120, description="Titre du film")
    year: int = Field(..., ge=1900, le=2025, description="Année de sortie")
    genre: str = Field(..., description="Genre du film")
    studio: str = Field(..., min_length=2, description="Studio de production")
    audience_score: int = Field(..., ge=0, le=100, description="Score audience (%)")
    profitability: float = Field(..., ge=0, description="Rentabilité")
    rotten_tomatoes: int = Field(..., ge=0, le=100, description="Score Rotten Tomatoes (%)")
    worldwide_gross: float = Field(..., ge=0, description="Recette mondiale")

    @field_validator('year')
    def year_cannot_be_future(cls, v):
        current_year = datetime.now().year
        if v > current_year:
            raise ValueError(f"L'année ne peut pas être dans le futur (année actuelle: {current_year})")
        return v

    @field_validator('genre')
    def genre_must_be_valid(cls, v):
        normalized_genre = v.strip().title()
        if normalized_genre not in VALID_GENRES:
            raise ValueError(f"Genre '{v}' non valide. Genres autorisés: {', '.join(VALID_GENRES)}")
        return normalized_genre

class MovieCreate(MovieBase):
    pass

class MovieUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=2, max_length=120, description="Titre du film")
    year: Optional[int] = Field(None, ge=1900, le=2025, description="Année de sortie")
    genre: Optional[str] = Field(None, description="Genre du film")
    studio: Optional[str] = Field(None, min_length=2, description="Studio de production")
    audience_score: Optional[int] = Field(None, ge=0, le=100, description="Score audience (%)")
    profitability: Optional[float] = Field(None, ge=0, description="Rentabilité")
    rotten_tomatoes: Optional[int] = Field(None, ge=0, le=100, description="Score Rotten Tomatoes (%)")
    worldwide_gross: Optional[float] = Field(None, ge=0, description="Recette mondiale")

    @field_validator('year')
    def year_cannot_be_future(cls, v):
        if v is not None:
            current_year = datetime.now().year
            if v > current_year:
                raise ValueError(f"L'année ne peut pas être dans le futur (année actuelle: {current_year})")
        return v

    @field_validator('genre')
    def genre_must_be_valid(cls, v):
        if v is not None:
            normalized_genre = v.strip().title()
            if normalized_genre not in VALID_GENRES:
                raise ValueError(f"Genre '{v}' non valide. Genres autorisés: {', '.join(VALID_GENRES)}")
            return normalized_genre
        return v

class Movie(MovieBase):
    id: int
    
    class Config:
        from_attributes = True

# NOUVEAUX Schémas d'authentification
class UserRegister(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6)
    role: str = Field(default="user")

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: str | None = None
    role: str | None = None