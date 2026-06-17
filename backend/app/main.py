"""نقطة دخول تطبيق FastAPI — رشاقة Backend."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import __version__
from .config import settings
from .routers import auth, favorites, foods, profile, recipes, targets

app = FastAPI(
    title="رشاقة API",
    description="واجهة برمجية لتطبيق حساب السعرات والتغذية للتخسيس الصحي.",
    version=__version__,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
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


@app.get("/", tags=["النظام"])
def root() -> dict:
    return {"app": "رشاقة", "version": __version__, "status": "ok"}


@app.get("/health", tags=["النظام"])
def health() -> dict:
    return {"status": "healthy"}
