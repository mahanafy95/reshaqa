"""نقطة دخول تطبيق FastAPI — رشاقة Backend."""
import math

from fastapi import FastAPI
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from slowapi.errors import RateLimitExceeded
from starlette.requests import Request
from starlette.responses import JSONResponse

from . import __version__
from .config import settings
from .core.ratelimit import limiter
from .routers import (
    admin,
    app_update,
    auth,
    billing,
    favorites,
    foods,
    health,
    issues,
    profile,
    recipes,
    reports,
    social,
    summary,
    targets,
    tracking,
)

_is_prod = settings.APP_ENV == "production"
app = FastAPI(
    title="رشاقة API",
    description="واجهة برمجية لتطبيق حساب السعرات والتغذية للتخسيس الصحي.",
    version=__version__,
    # إخفاء توثيق الـ API في الإنتاج (يقلّل الاستطلاع على نقاط الإشراف)
    docs_url=None if _is_prod else "/docs",
    redoc_url=None if _is_prod else "/redoc",
    openapi_url=None if _is_prod else "/openapi.json",
)


@app.on_event("startup")
def _bootstrap_admins() -> None:
    """إقلاع لمرة واحدة: ترقية الحسابات الموجودة التي أسماؤها ضمن ADMIN_USERNAMES.
    لا يُنشئ حسابات ولا يمنح صلاحية وقت الطلب — الفحص الحيّ على is_admin فقط."""
    names = settings.admin_usernames_set
    if not names:
        return
    try:
        from sqlalchemy import select

        from .database import SessionLocal
        from .models.user import User

        db = SessionLocal()
        try:
            changed = False
            for u in db.scalars(select(User)).all():
                if u.username.lower() in names and not u.is_admin:
                    u.is_admin = True
                    changed = True
            if changed:
                db.commit()
        finally:
            db.close()
    except Exception:
        pass  # لا نوقف الإقلاع بسبب خطأ مؤقت في قاعدة البيانات


# تحديد معدّل الطلبات (يُفعَّل في الإنتاج فقط) — يحمي نقاط المصادقة من التخمين والإغراق.
app.state.limiter = limiter


@app.exception_handler(RateLimitExceeded)
def _rate_limit_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    return JSONResponse(
        status_code=429,
        content={"detail": "محاولات كتير في وقت قصير. استنى شوية وحاول تاني."},
    )


def _strip_non_finite(obj):
    """يستبدل NaN/Infinity بـ None تكرارياً (غير متوافقة مع JSON القياسي)."""
    if isinstance(obj, float):
        return obj if math.isfinite(obj) else None
    if isinstance(obj, dict):
        return {k: _strip_non_finite(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_strip_non_finite(v) for v in obj]
    return obj


@app.exception_handler(RequestValidationError)
def _validation_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """يرجّع 422 نظيفاً حتى لو احتوى الإدخال على NaN/Infinity.

    المعالج الافتراضي يفشل (500) لأنه يحاول تهيئة قيمة NaN المُدخلة داخل تفاصيل الخطأ.
    """
    detail = _strip_non_finite(jsonable_encoder(exc.errors()))
    return JSONResponse(status_code=422, content={"detail": detail})


app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    # يقبل أي نطاق Vercel تلقائياً (لوحة الويب وكل نشرات المعاينة) بدون ضبط يدوي
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(profile.router)
app.include_router(targets.router)
app.include_router(foods.router)
app.include_router(recipes.router)
app.include_router(favorites.router)
app.include_router(tracking.router)
app.include_router(summary.router)
app.include_router(health.router)
app.include_router(reports.router)
app.include_router(app_update.router)
app.include_router(billing.router)
app.include_router(social.router)
app.include_router(issues.router)
app.include_router(admin.router)


@app.get("/", tags=["النظام"])
def root() -> dict:
    return {"app": "رشاقة", "version": __version__, "status": "ok"}


@app.get("/health", tags=["النظام"])
def health() -> dict:
    return {"status": "healthy"}
