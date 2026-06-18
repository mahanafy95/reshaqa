"""راوتر الوصفات — البناء بمكونات (مع خانة الزيت)، حساب الحلة ونصيب الفرد، وتسجيل النصيب."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..config import settings
from ..core.billing import PREMIUM_REQUIRED, is_user_premium
from ..core.deps import get_current_user
from ..database import get_db
from ..models.enums import FoodSource
from ..models.food import FoodLibrary, FoodLogged
from ..models.recipe import Recipe, RecipeIngredient
from ..models.user import User
from ..schemas.recipe import RecipeIn, RecipeIngredientIn, RecipeLogIn, RecipeOut
from ..schemas.food import FoodLogOut

router = APIRouter(prefix="/recipes", tags=["الوصفات"])


def _build_ingredient(db: Session, ing: RecipeIngredientIn) -> RecipeIngredient:
    """يبني مكوّناً بقيمه الإجمالية (لكامل كميته) من المكتبة أو من قيم لكل 100جم."""
    if ing.library_id is not None:
        lib = db.get(FoodLibrary, ing.library_id)
        if lib is None:
            raise HTTPException(status_code=404, detail=f"صنف المكتبة {ing.library_id} غير موجود.")
        name = ing.name_ar or lib.name_ar
        p100_cal, p100_p, p100_c, p100_f = lib.calories_per_100, lib.protein, lib.carbs, lib.fat
    else:
        name = ing.name_ar
        p100_cal = ing.per100_calories or 0
        p100_p = ing.per100_protein or 0
        p100_c = ing.per100_carbs or 0
        p100_f = ing.per100_fat or 0

    f = ing.amount_g / 100.0
    return RecipeIngredient(
        name_ar=name,
        amount=ing.amount_g,
        is_oil=ing.is_oil,
        calories=round(p100_cal * f, 1),
        protein=round(p100_p * f, 1),
        carbs=round(p100_c * f, 1),
        fat=round(p100_f * f, 1),
    )


def _apply_totals(recipe: Recipe) -> None:
    recipe.total_calories = round(sum(i.calories for i in recipe.ingredients), 1)
    recipe.total_protein = round(sum(i.protein for i in recipe.ingredients), 1)
    recipe.total_carbs = round(sum(i.carbs for i in recipe.ingredients), 1)
    recipe.total_fat = round(sum(i.fat for i in recipe.ingredients), 1)


def _to_out(recipe: Recipe) -> RecipeOut:
    out = RecipeOut.model_validate(recipe)
    s = recipe.servings or 1
    out.per_serving_calories = round(recipe.total_calories / s)
    out.per_serving_protein = round(recipe.total_protein / s, 1)
    out.per_serving_carbs = round(recipe.total_carbs / s, 1)
    out.per_serving_fat = round(recipe.total_fat / s, 1)
    return out


def _owned_recipe(db: Session, user_id: int, recipe_id: int) -> Recipe:
    r = db.scalar(select(Recipe).where(Recipe.id == recipe_id, Recipe.user_id == user_id))
    if r is None:
        raise HTTPException(status_code=404, detail="الوصفة غير موجودة.")
    return r


@router.post("", response_model=RecipeOut, status_code=status.HTTP_201_CREATED)
def create_recipe(
    payload: RecipeIn, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    # الطبقة المجانية: حد أقصى لعدد الوصفات المحفوظة؛ Premium بلا حدود
    if not is_user_premium(db, current_user.id):
        count = db.scalar(
            select(func.count()).select_from(Recipe).where(Recipe.user_id == current_user.id)
        ) or 0
        if count >= settings.FREE_RECIPE_LIMIT:
            raise HTTPException(
                status_code=PREMIUM_REQUIRED,
                detail={
                    "message": (
                        f"وصلت للحد المجاني ({settings.FREE_RECIPE_LIMIT} وصفات). "
                        "اشترك Premium لوصفات بلا حدود 💎"
                    ),
                    "premium_required": True,
                },
            )
    recipe = Recipe(user_id=current_user.id, name_ar=payload.name_ar, servings=payload.servings)
    recipe.ingredients = [_build_ingredient(db, ing) for ing in payload.ingredients]
    _apply_totals(recipe)
    db.add(recipe)
    db.commit()
    db.refresh(recipe)
    return _to_out(recipe)


@router.get("", response_model=list[RecipeOut])
def list_recipes(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    recipes = db.scalars(
        select(Recipe).where(Recipe.user_id == current_user.id).order_by(Recipe.created_at.desc())
    ).all()
    return [_to_out(r) for r in recipes]


@router.get("/{recipe_id}", response_model=RecipeOut)
def get_recipe(
    recipe_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    return _to_out(_owned_recipe(db, current_user.id, recipe_id))


@router.put("/{recipe_id}", response_model=RecipeOut)
def update_recipe(
    recipe_id: int,
    payload: RecipeIn,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    recipe = _owned_recipe(db, current_user.id, recipe_id)
    recipe.name_ar = payload.name_ar
    recipe.servings = payload.servings
    recipe.ingredients = [_build_ingredient(db, ing) for ing in payload.ingredients]
    _apply_totals(recipe)
    db.commit()
    db.refresh(recipe)
    return _to_out(recipe)


@router.delete("/{recipe_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_recipe(
    recipe_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    recipe = _owned_recipe(db, current_user.id, recipe_id)
    db.delete(recipe)
    db.commit()


@router.post("/{recipe_id}/log", response_model=FoodLogOut, status_code=status.HTTP_201_CREATED)
def log_recipe_portion(
    recipe_id: int,
    payload: RecipeLogIn,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """يسجّل نصيب المستخدم من الوصفة بدقة (حسب عدد الأنفار المتناوَلة)."""
    recipe = _owned_recipe(db, current_user.id, recipe_id)
    factor = payload.servings / (recipe.servings or 1)
    total_grams = sum(i.amount for i in recipe.ingredients)

    item = FoodLogged(
        user_id=current_user.id,
        date=payload.date,
        meal=payload.meal,
        name_ar=f"{recipe.name_ar} (نصيب)",
        amount=round(total_grams * factor, 1),
        calories=round(recipe.total_calories * factor),
        protein=round(recipe.total_protein * factor, 1),
        carbs=round(recipe.total_carbs * factor, 1),
        fat=round(recipe.total_fat * factor, 1),
        source=FoodSource.recipe,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item
