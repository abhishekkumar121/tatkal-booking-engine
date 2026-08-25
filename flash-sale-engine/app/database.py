# SQLAlchemy ka engine banane ke liye import; engine DB se connection manage karta hai.
from sqlalchemy import create_engine

# Base class banane ke liye import; isi Base se models/tables inherit karte hain.
from sqlalchemy.ext.declarative import declarative_base

# Session factory banane ke liye import; har request ke liye DB session milega.
from sqlalchemy.orm import sessionmaker

# Environment variables read karne ke liye Python ka built-in os module.
import os

# .env file ko load karne ke liye dotenv helper.
from dotenv import load_dotenv

# Project ki .env file read karke values environment variables mein daalta hai.
load_dotenv()

# .env se DATABASE_URL value uthata hai, jisme Postgres connection string hoti hai.
DATABASE_URL = os.getenv("DATABASE_URL")

# Database engine create karta hai; SQLAlchemy isi ke through DB se baat karega.
engine = create_engine(DATABASE_URL)

# SessionLocal ek factory hai jo new DB session banati hai.
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base woh parent class hai jisse User/Product jaise DB models banenge.
Base = declarative_base()

# FastAPI dependency function; routes isse DB session lete hain.
def get_db():
    # Ek naya database session open kar rahe hain.
    db = SessionLocal()
    # try block ensure karta hai ki route ko session mile.
    try:
        # yield ka matlab session route ko temporarily de do.
        yield db
    # finally block hamesha chalega, chahe route success ho ya error.
    finally:
        # Request complete hone ke baad DB session close kar rahe hain.
        db.close()
