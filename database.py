# database.py
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
import os

load_dotenv()

db_user = os.getenv('DB_USER', 'root')
db_pwd = os.getenv('DB_PWD', 'root')
db_name = os.getenv('DB_NAME', 'inherit')
db_url = os.getenv('DB_URL', 'localhost')
db_port = os.getenv('DB_PORT', '5432')

SQLALCHEMY_DATABASE_URL = f'postgresql+psycopg2://{db_user}:{db_pwd}@{db_url}:{db_port}/{db_name}'

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    pool_size=int(os.getenv("DB_POOL_SIZE", "10")),
    max_overflow=int(os.getenv("DB_MAX_OVERFLOW", "20")),
    pool_timeout=int(os.getenv("DB_POOL_TIMEOUT", "30")),
    pool_recycle=int(os.getenv("DB_POOL_RECYCLE", "1800")),
    pool_pre_ping=True,
)

Base = declarative_base()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()