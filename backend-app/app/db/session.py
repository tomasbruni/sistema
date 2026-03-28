from typing import Annotated

from fastapi import Depends
from sqlmodel import Session, SQLModel, create_engine

# =====================
# DATABASE CONFIG
# =====================

POSTGRES_USER = "fastapi_user"
POSTGRES_PASSWORD = "fastapi_pass"
POSTGRES_HOST = "localhost"
POSTGRES_PORT = "5432"
POSTGRES_DB = "fastapi_db"

DATABASE_URL = (
    f"postgresql+psycopg://{POSTGRES_USER}:{POSTGRES_PASSWORD}"
    f"@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"
)

engine = create_engine(DATABASE_URL, echo=True)

# =====================
# SESSION
# =====================

def get_session():
    with Session(engine) as session:
        yield session

SessionDep = Annotated[Session, Depends(get_session)]
