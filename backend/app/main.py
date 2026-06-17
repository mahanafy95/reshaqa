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
    favorites,
    foods,
    health,
    profile,
    recipes,
    reports,
    summary,
    targets,
    tracking,
)

app = FastAPI(
    title="رشاقة API",
    description="واجهة برمجية لتطبيق حساب السعرات والتغذية للتخسيس الصحي.",
    version=__version__,
)

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
app.include_router(admin.router)


@app.get("/", tags=["النظام"])
def root() -> dict:
    return {"app": "رشاقة", "version": __version__, "status": "ok"}


@app.get("/health", tags=["النظام"])
def health() -> dict:
    return {"status": "healthy"}
