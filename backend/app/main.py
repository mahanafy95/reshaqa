"""نقطة دخول تطبيق FastAPI — رشاقة Backend."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import __version__
from .config import settings
from .routers import (
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


@app.get("/", tags=["النظام"])
def root() -> dict:
    return {"app": "رشاقة", "version": __version__, "status": "ok"}


@app.get("/health", tags=["النظام"])
def health() -> dict:
    return {"status": "healthy"}
