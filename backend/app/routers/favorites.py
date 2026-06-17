"""راوتر المفضّلة — حفظ عناصر للإضافة السريعة + تسجيل سريع."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..core.deps import get_current_user
from ..database import get_db
from ..models.enums import FavoriteRefType, FoodSource
from ..models.favorite import Favorite
from ..models.food import FoodLibrary, FoodLogged
from ..models.recipe import Recipe
from ..models.user import User
from ..schemas.favorite import FavoriteIn, FavoriteLogIn, FavoriteOut
from ..schemas.food import FoodLogOut

router = APIRouter(prefix="/favorites", tags=["المفضّلة"])


def _owned_fav(db: Session, user_id: int, fav_id: int) -> Favorite:
    fav = db.scalar(select(Favorite).where(Favorite.id == fav_id, Favorite.user_id == user_id))
    if fav is None:
        raise HTTPException(status_code=404, detail="المفضّلة غير موجودة.")
    return fav


@router.post("", response_model=FavoriteOut, status_code=status.HTTP_201_CREATED)
def add_favorite(
    payload: FavoriteIn, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    fav = Favorite(user_id=current_user.id, ref_type=payload.ref_type,
                   default_amount=payload.default_amount)

    if payload.ref_type == FavoriteRefType.library:
        lib = db.get(FoodLibrary, payload.library_id)
        if lib is None:
            raise HTTPException(status_code=404, detail="صنف المكتبة غير موجود.")
        f = payload.default_amount / 100.0
        fav.ref_id = lib.id
        fav.name_ar = payload.name_ar or lib.name_ar
        fav.calories = round(lib.calories_per_100 * f)
        fav.protein = round(lib.protein * f, 1)
        fav.carbs = round(lib.carbs * f, 1)
        fav.fat = round(lib.fat * f, 1)

    elif payload.ref_type == FavoriteRefType.recipe:
        recipe = db.scalar(
            select(Recipe).where(Recipe.id == payload.recipe_id, Recipe.user_id == current_user.id)
        )
        if recipe is None:
            raise HTTPException(status_code=404, detail="الوصفة غير موجودة.")
        s = recipe.servings or 1
        fav.ref_id = recipe.id
        fav.name_ar = payload.name_ar or recipe.name_ar
        fav.default_amount = 1  # حصة واحدة
        fav.calories = round(recipe.total_calories / s)
        fav.protein = round(recipe.total_protein / s, 1)
        fav.carbs = round(recipe.total_carbs / s, 1)
        fav.fat = round(recipe.total_fat / s, 1)

    else:  # custom
        fav.ref_id = None
        fav.name_ar = payload.name_ar
        fav.calories = payload.calories or 0
        fav.protein = payload.protein or 0
        fav.carbs = payload.carbs or 0
        fav.fat = payload.fat or 0

    db.add(fav)
    db.commit()
    db.refresh(fav)
    return fav


@router.get("", response_model=list[FavoriteOut])
def list_favorites(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return db.scalars(
        select(Favorite).where(Favorite.user_id == current_user.id).order_by(Favorite.created_at.desc())
    ).all()


@router.delete("/{fav_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_favorite(
    fav_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    fav = _owned_fav(db, current_user.id, fav_id)
    db.delete(fav)
    db.commit()


@router.post("/{fav_id}/log", response_model=FoodLogOut, status_code=status.HTTP_201_CREATED)
def log_favorite(
    fav_id: int,
    payload: FavoriteLogIn,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """إضافة سريعة من المفضّلة لليوم/الوجبة."""
    fav = _owned_fav(db, current_user.id, fav_id)
    # القيم المخزّنة على default_amount؛ نضربها بالنسبة لو غُيّرت الكمية
    factor = (payload.amount / fav.default_amount) if (payload.amount and fav.default_amount) else 1.0
    amount = payload.amount or fav.default_amount

    item = FoodLogged(
        user_id=current_user.id,
        date=payload.date,
        meal=payload.meal,
        name_ar=fav.name_ar,
        amount=amount,
        calories=round(fav.calories * factor),
        protein=round(fav.protein * factor, 1),
        carbs=round(fav.carbs * factor, 1),
        fat=round(fav.fat * factor, 1),
        source=FoodSource.library if fav.ref_type == FavoriteRefType.library else FoodSource.manual,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item
