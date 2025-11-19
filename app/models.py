from sqlalchemy import Column, Integer, String, Float, CheckConstraint
from app.database import Base  

class Movie(Base):
    __tablename__ = "movies"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    genre = Column(String, nullable=False)
    studio = Column(String, nullable=False)
    audience_score = Column(Integer, nullable=False)
    profitability = Column(Float, nullable=False)
    rotten_tomatoes = Column(Integer, nullable=False)
    worldwide_gross = Column(Float, nullable=False)
    year = Column(Integer, nullable=False)

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, nullable=False, index=True)
    password = Column(String, nullable=False)
    role = Column(String, default="user", nullable=False)