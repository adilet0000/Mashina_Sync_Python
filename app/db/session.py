from sqlalchemy import Engine, create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from app.config import Settings


def get_catalog_database_url(settings: Settings) -> str | None:
    return settings.effective_catalog_database_url


def normalize_sqlalchemy_url(url: str) -> str:
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+psycopg://", 1)
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+psycopg://", 1)
    return url


def create_catalog_engine(settings: Settings) -> Engine | None:
    url = get_catalog_database_url(settings)
    if not url:
        return None

    return create_engine(
        normalize_sqlalchemy_url(url),
        pool_pre_ping=True,
        future=True,
    )


def create_catalog_session_factory(settings: Settings) -> sessionmaker[Session] | None:
    engine = create_catalog_engine(settings)
    if engine is None:
        return None

    return sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def ping_catalog_database(engine: Engine) -> None:
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))
