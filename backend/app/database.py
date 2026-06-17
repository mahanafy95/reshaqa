"""إعداد قاعدة البيانات (SQLAlchemy) — يدعم PostgreSQL و SQLite."""
from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from .config import settings

_db_url = settings.sqlalchemy_url
_is_sqlite = _db_url.startswith("sqlite")
_connect_args = {"check_same_thread": False} if _is_sqlite else {}

engine = create_engine(
    _db_url,
    connect_args=_connect_args,
    pool_pre_ping=not _is_sqlite,
    future=True,
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


class Base(DeclarativeBase):
    """الأساس لكل نماذج ORM."""


def get_db() -> Generator[Session, None, None]:
    """تبعية FastAPI لجلسة قاعدة بيانات لكل طلب."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
