"""إعدادات التطبيق — تُقرأ من متغيّرات البيئة أو ملف .env."""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # قاعدة البيانات — Postgres في الإنتاج، أو SQLite محلياً للتطوير/الاختبار
    DATABASE_URL: str = "sqlite:///./reshaqa_dev.db"

    # JWT
    JWT_SECRET_KEY: str = "dev-insecure-secret-change-me"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 43200  # 30 يوم

    # بيئة التشغيل
    APP_ENV: str = "development"
    APP_DEBUG: bool = True

    # CORS — قائمة مفصولة بفواصل
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:8080"

    # خدمة تقدير السعرات (Phase 3) — قابلة للتبديل
    CALORIE_ESTIMATOR_PROVIDER: str = "none"  # none | openai | nutrition_api
    OPENAI_API_KEY: str = ""
    NUTRITION_API_KEY: str = ""
    NUTRITION_API_BASE_URL: str = ""

    # الباركود (Phase 3)
    BARCODE_PROVIDER: str = "openfoodfacts"
    BARCODE_API_KEY: str = ""

    # OCR (Phase 3)
    OCR_PROVIDER: str = "none"  # none | tesseract | cloud_vision
    OCR_API_KEY: str = ""

    # هواوي الصحة (Phase 5)
    HUAWEI_HEALTH_CLIENT_ID: str = ""
    HUAWEI_HEALTH_CLIENT_SECRET: str = ""
    HUAWEI_HEALTH_REDIRECT_URI: str = ""

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
