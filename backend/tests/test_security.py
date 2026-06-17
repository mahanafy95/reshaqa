"""اختبارات أمان — رفض مفتاح JWT غير الآمن في الإنتاج."""
import pytest

from app.config import Settings


def test_production_rejects_insecure_jwt_secret():
    with pytest.raises(Exception):
        Settings(APP_ENV="production", JWT_SECRET_KEY="dev-insecure-secret-change-me", DATABASE_URL="sqlite://")


def test_production_rejects_empty_jwt_secret():
    with pytest.raises(Exception):
        Settings(APP_ENV="production", JWT_SECRET_KEY="", DATABASE_URL="sqlite://")


def test_production_accepts_strong_secret():
    s = Settings(APP_ENV="production", JWT_SECRET_KEY="x9f2-a-strong-random-secret-7c1e", DATABASE_URL="sqlite://")
    assert s.JWT_SECRET_KEY


def test_development_allows_default_secret():
    s = Settings(APP_ENV="development", JWT_SECRET_KEY="dev-insecure-secret-change-me", DATABASE_URL="sqlite://")
    assert s.APP_ENV == "development"
