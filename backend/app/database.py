"""إعداد قاعدة البيانات (SQLAlchemy) — يدعم PostgreSQL و SQLite."""
from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from .config import settings

_db_url = settings.sqlalchemy_url
_is_sqlite = _db_url.startswith("sqlite")
_connect_args = {"check_same_thread": False} if _is_sqlite else {}

_engine_kwargs: dict = {"connect_args": _connect_args, "future": True}
if not _is_sqlite:
    # ضبط تجمّع الاتصالات لحدود Neon المجانية:
    # pool_recycle أقل من مهلة تعليق Neon (5 دقائق) لإسقاط الاتصالات قبل أن تتعطّل،
    # وحجم تجمّع محدود حتى لا نتخطّى سقف اتصالات الطبقة المجانية.
    _engine_kwargs.update(
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=5,
        pool_recycle=280,
    )

engine = create_engine(_db_url, **_engine_kwargs)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


class Base(DeclarativeBase):
    """الأساس لكل نماذج ORM."""


def get_db() -> Generator[Session, None, None]:
    """تبعية FastAPI لجلسة قاعدة بيانات لكل طلب.

    أي استثناء في الطلب → نتراجع (rollback) عن أي معاملة معلّقة قبل ما الجلسة ترجع
    للتجمّع، عشان منرجّعش جلسة «متّسخة» للطلب اللي بعده ولا نسيب صفوف منضافة جزئياً.
    """
    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
