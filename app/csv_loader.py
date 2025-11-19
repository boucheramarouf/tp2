from app.models import Movie
from app.database import Base, engine, SessionLocal
import csv
import os
import re
import logging
import datetime
from sqlalchemy.orm import Session
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
CSV_PATH = BASE_DIR / "data" / "movies.csv"
LOG_FILE = "import_errors.log"

logger = logging.getLogger("movies_import")
logger.setLevel(logging.INFO)
fh = logging.FileHandler(LOG_FILE, encoding="utf-8")
fh.setLevel(logging.INFO)
logger.addHandler(fh)

def normalize_gross(value):
    if not value:
        return None
    cleaned = re.sub(r'[\$,]', '', str(value))
    try:
        return float(cleaned)
    except:
        return None

def normalize_percent(value):
    if not value:
        return None
    cleaned = str(value).replace('%', '').strip()
    try:
        return int(float(cleaned))
    except:
        return None

def normalize_float(value):
    if not value:
        return None
    try:
        return float(value)
    except:
        return None

def is_database_empty(db: Session) -> bool:
    """Vérifie si la table movies contient déjà des données"""
    try:
        return db.query(Movie).count() == 0
    except:
        
        return True

def import_csv_to_db(csv_path=CSV_PATH):
    """Charge le CSV seulement si la base est vide"""
    
    
    Base.metadata.create_all(bind=engine)
    db: Session = SessionLocal()
    
    
    if not is_database_empty(db):
        print("La base contient déjà des données, import ignoré.")
        db.close()
        return
    
   
    if not os.path.exists(csv_path):
        print(f"ERREUR: Fichier CSV introuvable: {csv_path}")
        print(f"Recherché dans: {os.path.abspath(csv_path)}")
        db.close()
        return
    
    print(f"Import des données depuis: {csv_path}")
    inserted = duplicates = logged = 0

    logger.info(f"Import started: {datetime.datetime.utcnow().isoformat()}")

    try:
        with open(csv_path, newline='', encoding="utf-8") as f:
            reader = csv.DictReader(f)

            
            print(f"En-têtes CSV: {reader.fieldnames}")

            for i, row in enumerate(reader, start=1):
                
                title = row.get("Film") 
                year = row.get("Year")
                genre = row.get("Genre")
                studio = row.get("Lead Studio")

                aud = row.get("Audience score %")
                rt = row.get("Rotten Tomatoes %")
                profitability = row.get("Profitability")
                gross = row.get("Worldwide Gross")

                
                if i == 1:
                    print(f"Première ligne: {row}")

                
                if not title or not year or not genre or not studio:
                    print(f"Ligne {i} ignorée - champs manquants: title={title}, year={year}, genre={genre}, studio={studio}")
                    logger.info(f"Row {i}: missing fields -> {row}")
                    logged += 1
                    continue

                try:
                    year = int(year)
                except:
                    print(f"Ligne {i} ignorée - année invalide: {year}")
                    logger.info(f"Row {i}: invalid year -> {row}")
                    logged += 1
                    continue

               
                gross = normalize_gross(gross)
                audience_score = normalize_percent(aud)
                rotten_tomatoes = normalize_percent(rt)
                profitability = normalize_float(profitability)

              
                if i <= 3: 
                    print(f"Ligne {i} normalisée: audience={audience_score}, rotten={rotten_tomatoes}, profit={profitability}, gross={gross}")

                
                if audience_score is None or rotten_tomatoes is None or profitability is None or gross is None:
                    print(f"Ligne {i} ignorée - données numériques invalides: audience={audience_score}, rotten={rotten_tomatoes}, profit={profitability}, gross={gross}")
                    logger.info(f"Row {i}: invalid numeric data -> {row}")
                    logged += 1
                    continue

               
                exists = db.query(Movie).filter(Movie.title == title, Movie.year == year).first()
                if exists:
                    duplicates += 1
                    continue

               
                movie = Movie(
                    title=title,
                    year=year,
                    genre=genre,
                    studio=studio,
                    worldwide_gross=gross,
                    audience_score=audience_score,
                    rotten_tomatoes=rotten_tomatoes,
                    profitability=profitability
                )

                db.add(movie)
                inserted += 1

              
                if inserted % 10 == 0:
                    print(f"{inserted} films importés...")

      
        db.commit()
        print(f"Import terminé: {inserted} films insérés, {duplicates} doublons, {logged} lignes ignorées")
        
    except Exception as e:
        print(f"Erreur lors de l'import: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
    finally:
        db.close()

    logger.info(
        f"Import finished: inserted={inserted}, duplicates={duplicates}, logged={logged}"
    )