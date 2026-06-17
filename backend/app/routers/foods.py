"""راوتر تسجيل الأكل — CRUD + بحث المكتبة + تقدير + باركود + ملصق + اقتراحات."""
from datetime import date as date_type

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from ..core.deps import get_current_user
from ..database import get_db
from ..models.enums import FoodSource
from ..models.favorite import Favorite
from ..models.food import FoodLibrary, FoodLogged
from ..models.recipe import Recipe
from ..models.user import User
from ..schemas.food import (
    BarcodeOut,
    EstimateOut,
    FoodLibraryOut,
    FoodLogIn,
    FoodLogOut,
    FoodLogUpdate,
    LabelParseOut,
    SuggestionOut,
)
from ..services import barcode as barcode_svc
from ..services import ocr as ocr_svc
from ..services.estimator import get_estimator

router = APIRouter(prefix="/foods", tags=["تسجيل الأكل"])


def _owned_log(db: Session, user_id: int, food_id: int) -> FoodLogged:
    item = db.scalar(
        select(FoodLogged).where(FoodLogged.id == food_id, FoodLogged.user_id == user_id)
    )
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="العنصر غير موجود.")
    return item


# ---------- البحث في المكتبة ----------
@router.get("/library/search", response_model=list[FoodLibraryOut])
def search_library(
    q: str = Query("", description="نص البحث"),
    region: str | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    stmt = select(FoodLibrary)
    if q.strip():
        stmt = stmt.where(FoodLibrary.name_ar.ilike(f"%{q.strip()}%"))
    if region:
        stmt = stmt.where(FoodLibrary.region == region)
    stmt = stmt.order_by(FoodLibrary.name_ar).limit(limit)
    return db.scalars(stmt).all()


@router.get("/library/{lib_id}", response_model=FoodLibraryOut)
def get_library_item(
    lib_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    item = db.get(FoodLibrary, lib_id)
    if item is None:
        raise HTTPException(status_code=404, detail="الصنف غير موجود.")
    return item


# ---------- التقدير التلقائي ----------
@router.get("/estimate", response_model=EstimateOut)
def estimate_food(
    name: str = Query(..., min_length=1),
    amount: float = Query(100, gt=0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """تقدير سعرات أكلة بالاسم — يجرّب المكتبة أولاً ثم heuristic (لا يطلب رقماً)."""
    # محاولة مطابقة المكتبة أولاً (أدق)
    match = db.scalar(
        select(FoodLibrary).where(FoodLibrary.name_ar.ilike(f"%{name.strip()}%")).limit(1)
    )
    if match is not None:
        f = amount / 100.0
        return EstimateOut(
            name_ar=match.name_ar,
            amount_g=amount,
            calories=round(match.calories_per_100 * f),
            protein=round(match.protein * f, 1),
            carbs=round(match.carbs * f, 1),
            fat=round(match.fat * f, 1),
            per100_calories=match.calories_per_100,
            confidence="high",
            note_ar="من مكتبة الأكلات.",
            source=FoodSource.library,
        )

    est = get_estimator().estimate(name, amount)
    return EstimateOut(
        name_ar=est.name_ar,
        amount_g=est.amount_g,
        calories=est.calories,
        protein=est.protein,
        carbs=est.carbs,
        fat=est.fat,
        per100_calories=est.per100_calories,
        confidence=est.confidence,
        note_ar=est.note_ar,
        source=FoodSource.estimated,
    )


# ---------- الباركود ----------
@router.get("/barcode/{code}", response_model=BarcodeOut)
def lookup_barcode(
    code: str, current_user: User = Depends(get_current_user)
):
    result = barcode_svc.fetch_barcode(code)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="مالقيناش المنتج ده بالباركود. تقدر تضيفه يدوياً.",
        )
    return BarcodeOut(
        barcode=result.barcode,
        name_ar=result.name_ar,
        calories_per_100=result.calories_per_100,
        protein=result.protein,
        carbs=result.carbs,
        fat=result.fat,
    )


# ---------- ملصق التغذية (OCR) ----------
@router.post("/label", response_model=LabelParseOut)
async def parse_label(
    text: str | None = Form(None),
    image: UploadFile | None = File(None),
    current_user: User = Depends(get_current_user),
):
    """يستخرج القيم من نص ملصق (مُدخل/مُستخرج) أو من صورة لو OCR مُهيّأ."""
    raw = text
    if not raw and image is not None:
        content = await image.read()
        raw = ocr_svc.ocr_image_to_text(content)
        if not raw:
            return LabelParseOut(
                calories=None, protein=None, carbs=None, fat=None,
                basis_ar="غير محدد",
                note_ar="محرك OCR غير مُفعّل على الخادم. اكتب القيم يدوياً أو فعّل OCR_PROVIDER.",
            )
    if not raw:
        raise HTTPException(status_code=422, detail="مفيش نص أو صورة للتحليل.")

    ex = ocr_svc.parse_nutrition_text(raw)
    return LabelParseOut(
        calories=ex.calories, protein=ex.protein, carbs=ex.carbs, fat=ex.fat,
        basis_ar=ex.basis_ar,
        note_ar="راجع القيم وعدّلها قبل الحفظ." if ex.calories else "ما قدرناش نستخرج السعرات — اكتبها يدوياً.",
    )


# ---------- اقتراحات عند الكتابة ----------
@router.get("/suggest", response_model=list[SuggestionOut])
def suggest(
    q: str = Query(..., min_length=1),
    limit: int = Query(10, ge=1, le=30),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """اقتراحات من المكتبة + وصفات المستخدم + مفضّلاته."""
    like = f"%{q.strip()}%"
    out: list[SuggestionOut] = []

    for r in db.scalars(
        select(Recipe).where(Recipe.user_id == current_user.id, Recipe.name_ar.ilike(like)).limit(limit)
    ).all():
        per = r.total_calories / r.servings if r.servings else r.total_calories
        out.append(SuggestionOut(kind="recipe", ref_id=r.id, name_ar=r.name_ar,
                                  calories_per_serving=round(per)))

    for fav in db.scalars(
        select(Favorite).where(Favorite.user_id == current_user.id, Favorite.name_ar.ilike(like)).limit(limit)
    ).all():
        out.append(SuggestionOut(kind="favorite", ref_id=fav.id, name_ar=fav.name_ar,
                                  calories_per_serving=fav.calories))

    remaining = max(limit - len(out), 0)
    if remaining:
        for lib in db.scalars(
            select(FoodLibrary).where(FoodLibrary.name_ar.ilike(like)).order_by(FoodLibrary.name_ar).limit(remaining)
        ).all():
            out.append(SuggestionOut(kind="library", ref_id=lib.id, name_ar=lib.name_ar,
                                     calories_per_100=lib.calories_per_100, region=lib.region))
    return out[:limit]


# ---------- CRUD تسجيل الأكل ----------
@router.post("", response_model=FoodLogOut, status_code=status.HTTP_201_CREATED)
def add_food(
    payload: FoodLogIn, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    item = FoodLogged(user_id=current_user.id, **payload.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.get("", response_model=list[FoodLogOut])
def list_foods(
    on: date_type | None = Query(None, description="اليوم (افتراضياً النهاردة)"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    day = on or date_type.today()
    stmt = (
        select(FoodLogged)
        .where(FoodLogged.user_id == current_user.id, FoodLogged.date == day)
        .order_by(FoodLogged.created_at)
    )
    return db.scalars(stmt).all()


@router.put("/{food_id}", response_model=FoodLogOut)
def update_food(
    food_id: int,
    payload: FoodLogUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    item = _owned_log(db, current_user.id, food_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(item, field, value)
    db.commit()
    db.refresh(item)
    return item


@router.delete("/{food_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_food(
    food_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    item = _owned_log(db, current_user.id, food_id)
    db.delete(item)
    db.commit()
