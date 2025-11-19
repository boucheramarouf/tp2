from fastapi import FastAPI, Depends
from contextlib import asynccontextmanager
from app.database import Base, engine
from app.csv_loader import import_csv_to_db
from app.routes import router, auth_router, admin_router  # MODIFICATION
import datetime
from sqlalchemy.orm import Session
from app.dependencies import get_db
from app.models import Movie

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("FastAPI démarre. Initialisation de la base de données...")
    
    Base.metadata.create_all(bind=engine)
    
    try:
        import_csv_to_db()
        print("Import CSV terminé avec succès")
    except Exception as e:
        print(f"Erreur lors de l'import CSV: {e}")
    
    yield 
    
    print("FastAPI s'arrête.")

app = FastAPI(lifespan=lifespan, title="Movies API", version="1.0.0")

# Inclure tous les routers
app.include_router(router)
app.include_router(auth_router)  # AJOUT
app.include_router(admin_router)  # AJOUT

@app.get("/")
def root():
    return {"message": "Movies API is running"}

@app.get("/health")
def health_check(db: Session = Depends(get_db)):
    """Endpoint de santé de l'API"""
    try:
        movie_count = db.query(Movie).count()
        
        return {
            "status": "healthy",
            "timestamp": datetime.datetime.utcnow().isoformat(),
            "database": "connected",
            "movie_count": movie_count,
            "version": "1.0.0"
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "timestamp": datetime.datetime.utcnow().isoformat(),
            "database": "disconnected",
            "error": str(e),
            "movie_count": 0
        }