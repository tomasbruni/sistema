import os
from typing import Annotated

from fastapi import Depends
from sqlmodel import Session, SQLModel, create_engine

# =====================
# DATABASE CONFIG
# =====================

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql+psycopg://fastapi_user:fastapi_pass@localhost:5432/fastapi_db",
)

# Render usa "postgres://" pero SQLAlchemy necesita "postgresql://"
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+psycopg://", 1)
elif DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg://", 1)

engine = create_engine(DATABASE_URL, echo=False)

# =====================
# SESSION
# =====================

def get_session():
    with Session(engine) as session:
        yield session

SessionDep = Annotated[Session, Depends(get_session)]
