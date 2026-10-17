from collections.abc import Iterator

from sqlalchemy import Engine
from sqlmodel import Session, SQLModel, create_engine

from app import config

engine = create_engine(config.DATABASE_URL, connect_args={"check_same_thread": False})


def init_db(bind: Engine = engine) -> None:
    SQLModel.metadata.create_all(bind)


def drop_db(bind: Engine = engine) -> None:
    SQLModel.metadata.drop_all(bind)


def get_session() -> Iterator[Session]:
    with Session(engine) as session:
        yield session
