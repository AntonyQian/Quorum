from collections.abc import Iterator

from sqlmodel import Session, SQLModel, create_engine

from app import config

engine = create_engine(config.DATABASE_URL, connect_args={"check_same_thread": False})


def init_db() -> None:
    SQLModel.metadata.create_all(engine)


def drop_db() -> None:
    SQLModel.metadata.drop_all(engine)


def get_session() -> Iterator[Session]:
    with Session(engine) as session:
        yield session
