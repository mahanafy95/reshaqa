"""إعدادات التطبيق — تُقرأ من متغيّرات البيئة أو ملف .env."""
from functools import lru_cache

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_INSECURE_SECRETS = {"", "dev-insecure-secret-change-me", "change-me-to-a-long-random-secret"}


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

    # المشرفون (سوبر أدمن) — أسماء مستخدمين مفصولة بفواصل تُمنح صلاحية الإشراف تلقائياً
    ADMIN_USERNAMES: str = ""

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

    # تسجيل الدخول بجوجل (مجاني تماماً — Google Identity، مش Firebase)
    # معرّفات العميل المسموح بها (جمهور الرمز aud) مفصولة بفواصل: عميل الويب (+ الأندرويد لاحقاً)
    GOOGLE_CLIENT_IDS: str = ""

    # البريد (مجاني) — لإرسال رمز إعادة تعيين كلمة السر بالإيميل (بدون أي SMS)
    # المزوّد: gmail (SMTP عبر كلمة مرور تطبيق) أو brevo (HTTPS احتياطي لو Render حجب SMTP)
    EMAIL_PROVIDER: str = "gmail"  # gmail | brevo | none
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 465
    SMTP_USERNAME: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM: str = ""
    SMTP_FROM_NAME: str = "رشاقة"
    BREVO_API_KEY: str = ""
    # مدة صلاحية رمز إعادة التعيين (بالدقائق) وأقصى عدد محاولات تحقّق
    OTP_TTL_MINUTES: int = 15
    OTP_MAX_ATTEMPTS: int = 5

    # ===== الاشتراكات (Google Play Billing) =====
    # حساب خدمة Google Play (محتوى ملف JSON كنص) للتحقق من المشتريات من جهة الخادم
    GOOGLE_PLAY_SERVICE_ACCOUNT_JSON: str = ""
    GOOGLE_PLAY_PACKAGE_NAME: str = "com.reshaqa.reshaqa"
    # معرّفات منتجات الاشتراك المقبولة (مفصولة بفواصل)
    GOOGLE_PLAY_PRODUCT_IDS: str = "reshaqa_premium"
    # رمز تحقّق ويبهوك Pub/Sub (RTDN) — يُمرَّر كـ ?token=... ويُطابَق
    PUBSUB_VERIFICATION_TOKEN: str = ""
    # حدود الطبقة المجانية
    FREE_RECIPE_LIMIT: int = 3

    # المساعد الصحي بالذكاء الاصطناعي — Google Gemini (الباقة المجانية، بدون فيزا)
    # مفتاح مجاني من https://aistudio.google.com/apikey . لو فاضي، يفضل المحلّل المحلي (heuristic).
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-2.0-flash"

    # مزوّد مجاني سريع وموثوق — Groq (باقة مجانية سخيّة، بدون فيزا).
    # مفتاح من https://console.groq.com/keys . يُجرَّب قبل OpenRouter (أعلى حصّة وأسرع).
    GROQ_API_KEY: str = ""
    # موديلات Groq بالترتيب (مفصولة بفواصل) — نجرّبها واحدة تلو الأخرى.
    GROQ_MODELS: str = "llama-3.3-70b-versatile,llama-3.1-8b-instant"

    # مزوّد مجاني سريع جداً وموثوق — Cerebras (باقة مجانية سخيّة، بدون فيزا).
    # مفتاح من https://cloud.cerebras.ai . يُجرَّب بعد Groq وقبل OpenRouter.
    CEREBRAS_API_KEY: str = ""
    # موديلات Cerebras بالترتيب (مفصولة بفواصل). عدّلها لو اسم موديل اتغيّر.
    CEREBRAS_MODELS: str = "llama-3.3-70b,llama3.1-8b"

    # احتياطي مجاني عبر OpenRouter — مفتاح واحد يفتح موديلات مجانية (DeepSeek/Qwen/GLM الصينية وغيرها).
    # مفتاح من https://openrouter.ai/keys . لو فاضي، نكتفي بالمزوّدات الأخرى أو المحلّل المحلي.
    OPENROUTER_API_KEY: str = ""
    # قائمة موديلات OpenRouter (مفصولة بفواصل). فاضية = اكتشاف تلقائي للموديلات
    # المجانية المتاحة لحظياً (يتداوى ذاتياً لو OpenRouter غيّر الأسماء). عيّنها فقط
    # لو عايز تثبّت موديلات بعينها.
    OPENROUTER_MODELS: str = ""

    @model_validator(mode="after")
    def _enforce_secure_secret(self):
        # في الإنتاج: ارفض التشغيل بمفتاح JWT افتراضي/فارغ (يمنع تزوير التوكنات)
        if self.APP_ENV != "development" and self.JWT_SECRET_KEY in _INSECURE_SECRETS:
            raise ValueError(
                "JWT_SECRET_KEY لازم يكون مفتاح قوي وسرّي في الإنتاج "
                "(عيّن متغيّر البيئة JWT_SECRET_KEY)."
            )
        return self

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    @property
    def admin_usernames_set(self) -> set[str]:
        return {u.strip().lower() for u in self.ADMIN_USERNAMES.split(",") if u.strip()}

    @property
    def google_client_ids_set(self) -> set[str]:
        return {c.strip() for c in self.GOOGLE_CLIENT_IDS.split(",") if c.strip()}

    @property
    def google_login_enabled(self) -> bool:
        return bool(self.google_client_ids_set)

    @property
    def email_from_address(self) -> str:
        return (self.SMTP_FROM or self.SMTP_USERNAME).strip()

    @property
    def email_enabled(self) -> bool:
        """هل إرسال البريد مضبوط؟ (Gmail SMTP أو Brevo)."""
        if self.EMAIL_PROVIDER == "gmail":
            return bool(self.SMTP_HOST and self.SMTP_USERNAME and self.SMTP_PASSWORD)
        if self.EMAIL_PROVIDER == "brevo":
            return bool(self.BREVO_API_KEY and self.email_from_address)
        return False

    @property
    def play_product_ids_set(self) -> set[str]:
        return {p.strip() for p in self.GOOGLE_PLAY_PRODUCT_IDS.split(",") if p.strip()}

    @property
    def billing_enabled(self) -> bool:
        """هل التحقّق من مشتريات Play مضبوط؟ (حساب الخدمة موجود)."""
        return bool(self.GOOGLE_PLAY_SERVICE_ACCOUNT_JSON.strip())

    @property
    def openrouter_models_list(self) -> list[str]:
        """قائمة موديلات OpenRouter المنظّفة (بدون فراغات أو عناصر فارغة)."""
        return [m.strip() for m in self.OPENROUTER_MODELS.split(",") if m.strip()]

    @property
    def groq_models_list(self) -> list[str]:
        """قائمة موديلات Groq المنظّفة (بدون فراغات أو عناصر فارغة)."""
        return [m.strip() for m in self.GROQ_MODELS.split(",") if m.strip()]

    @property
    def cerebras_models_list(self) -> list[str]:
        """قائمة موديلات Cerebras المنظّفة (بدون فراغات أو عناصر فارغة)."""
        return [m.strip() for m in self.CEREBRAS_MODELS.split(",") if m.strip()]

    @property
    def ai_enabled(self) -> bool:
        """هل المساعد الذكي مفعّل؟ (أي مزوّد: Gemini/Groq/Cerebras/OpenRouter — وإلا المحلّل المحلي)."""
        return (
            bool(self.GEMINI_API_KEY.strip())
            or bool(self.GROQ_API_KEY.strip())
            or bool(self.CEREBRAS_API_KEY.strip())
            or bool(self.OPENROUTER_API_KEY.strip())
        )

    @property
    def sqlalchemy_url(self) -> str:
        """عنوان متوافق مع psycopg3 — يطبّع صيغة Railway (postgresql://) تلقائياً."""
        url = self.DATABASE_URL
        if url.startswith("postgresql://"):
            url = "postgresql+psycopg://" + url[len("postgresql://"):]
        elif url.startswith("postgres://"):  # صيغة قديمة من بعض المزوّدين
            url = "postgresql+psycopg://" + url[len("postgres://"):]
        return url


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
