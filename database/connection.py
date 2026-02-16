import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv

load_dotenv_path = os.path.join(os.path.dirname(__file__), '..', 'docker-evolution', '.env')
load_dotenv(load_dotenv_path)

DATABASE_URL = os.getenv("DATABASE_CONNECTION_URI_ALQ", "postgresql://user:pass@localhost:5432/medical_db")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()