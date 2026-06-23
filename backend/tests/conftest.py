"""تهيئة الاختبارات — قاعدة بيانات SQLite في الذاكرة معزولة لكل اختبار."""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import models  # noqa: F401  (تسجيل كل الجداول)
from app.config import settings
from app.database import Base, get_db
from app.main import app


@pytest.fixture(autouse=True)
def _no_external_food_lookup():
    """نوقّف البحث الغذائي الخارجي (OpenFoodFacts/Gemini) في الاختبارات — بلا شبكة."""
    original = settings.FOOD_LOOKUP_ENABLED
    settings.FOOD_LOOKUP_ENABLED = False
    try:
        yield
    finally:
        settings.FOOD_LOOKUP_ENABLED = original


@pytest.fixture
def db_session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def auth_headers(client: TestClient, username: str = "ahmed", password: str = "pass1234") -> dict:
    """تسجّل مستخدماً وتُرجع ترويسة Authorization جاهزة."""
    r = client.post("/auth/register", json={"username": username, "password": password})
    assert r.status_code in (201, 409), r.text
    if r.status_code == 409:
        r = client.post("/auth/login", json={"username": username, "password": password})
    token = r.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def make_premium(db_session, username: str, *, status: str = "active", days: int = 30):
    """يمنح المستخدم اشتراكاً مفعّلاً (للاختبارات التي تستخدم ميزات Premium)."""
    from datetime import datetime, timedelta, timezone

    from sqlalchemy import select

    from app.models.subscription import Subscription
    from app.models.user import User

    user = db_session.scalar(select(User).where(User.username == username))
    sub = db_session.scalar(select(Subscription).where(Subscription.user_id == user.id))
    if sub is None:
        sub = Subscription(user_id=user.id)
        db_session.add(sub)
    sub.platform = "google_play"
    sub.product_id = "reshaqa_premium"
    sub.purchase_token = f"test-token-{username}"
    sub.status = status
    sub.current_period_end = datetime.now(timezone.utc) + timedelta(days=days)
    sub.auto_renewing = True
    db_session.commit()
    return sub
