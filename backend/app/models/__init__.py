"""تجميع كل نماذج ORM — استيرادها هنا يضمن تسجيلها في Base.metadata (مهم لـ Alembic)."""
from .enums import (
    ActivityLevel,
    ActivitySource,
    FavoriteRefType,
    FoodSource,
    Meal,
    Region,
    Sex,
    TargetMode,
)
from .favorite import Favorite
from .food import FoodLibrary, FoodLogged
from .health import HealthToken
from .profile import Profile
from .recipe import Recipe, RecipeIngredient
from .targets import DailyTarget
from .tracking import ActivityLog, MoodLog, WaistLog, WaterLog, WeightLog
from .user import User

__all__ = [
    "ActivityLevel",
    "ActivitySource",
    "FavoriteRefType",
    "FoodSource",
    "Meal",
    "Region",
    "Sex",
    "TargetMode",
    "User",
    "Profile",
    "DailyTarget",
    "FoodLibrary",
    "FoodLogged",
    "HealthToken",
    "Recipe",
    "RecipeIngredient",
    "Favorite",
    "WeightLog",
    "WaistLog",
    "WaterLog",
    "ActivityLog",
    "MoodLog",
]
