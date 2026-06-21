"""راوتر تسجيل الأكل — CRUD + بحث المكتبة + تقدير + باركود + ملصق + اقتراحات."""
from datetime import date as date_type

import re

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Request, UploadFile, status
from sqlalchemy import case, func, or_, select
from sqlalchemy.orm import Session

from ..config import settings
from ..core.billing import require_premium
from ..core.deps import get_current_user
from ..core.ratelimit import limiter
from ..database import get_db
from ..models.enums import FoodSource, Meal
from ..models.favorite import Favorite
from ..models.food import FoodLibrary, FoodLogged
from ..models.recipe import Recipe
from ..models.user import User
from ..schemas.food import (
    BarcodeIn,
    BarcodeOut,
    EstimateOut,
    FoodLibraryOut,
    FoodLogIn,
    FoodLogOut,
    FoodLogUpdate,
    LabelParseOut,
    ParsedFoodItem,
    ParseRequest,
    ParseResponse,
    SuggestionOut,
)
from ..services import ai_assistant
from ..services import barcode as barcode_svc
from ..services import meal_parser
from ..services import ocr as ocr_svc
from ..services.estimator import get_estimator

router = APIRouter(prefix="/foods", tags=["تسجيل الأكل"])

# أقصى نسبة طول مسموح بها بين اسم المكتبة والاستعلام عند المطابقة الجزئية (احتواء).
# يمنع «نص رغيف عيش» من مطابقة «ساندويتش فلافل بالعيش» (اسم أطول بكتير وغير متعلّق).
_MATCH_LEN_RATIO = 2.5


def _match_library(db: Session, name: str) -> FoodLibrary | None:
    """يلاقي أقرب صنف مكتبة لاسم مُدخل — مع تجنّب مطابقة استعلام قصير لاسم أطول غير متعلّق.

    الأولوية:
      1) تطابق تام للاسم (تجاهل حالة الأحرف/المسافات).
      2) اسم يبدأ بالاستعلام.
      3) أقصر اسم مكتبة يحتوي الاستعلام، بشرط ألا يتجاوز طوله ~2.5 ضعف طول الاستعلام
         (إلا لو كان يبدأ بالاستعلام).
    لو مفيش تطابق جيد، يرجّع None (فيستخدم المقدّر).
    """
    q = (name or "").strip()
    if not q:
        return None
    ql = q.lower()

    # 1) تطابق تام (lower) — أدق ما يكون
    exact = db.scalar(
        select(FoodLibrary)
        .where(func.lower(FoodLibrary.name_ar) == ql)
        .order_by(func.length(FoodLibrary.name_ar))
        .limit(1)
    )
    if exact is not None:
        return exact

    # 2) اسم يبدأ بالاستعلام (نختار الأقصر)
    starts = db.scalar(
        select(FoodLibrary)
        .where(func.lower(FoodLibrary.name_ar).like(f"{ql}%"))
        .order_by(func.length(FoodLibrary.name_ar))
        .limit(1)
    )
    if starts is not None:
        return starts

    # 3) أقصر اسم يحتوي الاستعلام، مع حدّ على فرق الطول
    contains = db.scalar(
        select(FoodLibrary)
        .where(func.lower(FoodLibrary.name_ar).like(f"%{ql}%"))
        .order_by(func.length(FoodLibrary.name_ar))
        .limit(1)
    )
    if contains is not None and len(contains.name_ar.strip()) <= len(q) * _MATCH_LEN_RATIO:
        return contains
    return None


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
    query = q.strip()
    if query:
        stmt = stmt.where(FoodLibrary.name_ar.ilike(f"%{query}%"))
    if region:
        stmt = stmt.where(FoodLibrary.region == region)
    if query:
        # الأقرب أولاً: تطابق تام ثم اسم يبدأ بالاستعلام ثم الأقصر، فالأبجدي.
        ql = query.lower()
        rank = case(
            (func.lower(FoodLibrary.name_ar) == ql, 0),
            (func.lower(FoodLibrary.name_ar).like(f"{ql}%"), 1),
            else_=2,
        )
        stmt = stmt.order_by(rank, func.length(FoodLibrary.name_ar), FoodLibrary.name_ar)
    else:
        stmt = stmt.order_by(FoodLibrary.name_ar)
    stmt = stmt.limit(limit)
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
    # محاولة مطابقة المكتبة أولاً (أدق) — مطابقة محكمة تتجنّب التطابق الجزئي الخاطئ
    match = _match_library(db, name)
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


# ---------- المحلّل الذكي (اكتب/كلّم بالكلام) ----------
def _fmt_qty(it: ParsedFoodItem) -> str:
    q = int(it.qty) if it.qty == int(it.qty) else it.qty
    if it.unit:
        return f"{q} {it.unit}"
    # صنف معدود بدون وحدة (زي «بيضتين» أو «3 تفاح») — نوضّح العدد مع الجرامات
    if isinstance(q, int) and q >= 2:
        return f"عدد {q} ({round(it.grams)} جم)"
    return f"{round(it.grams)} جم"


def _build_reply(items: list[ParsedFoodItem], total: float, logged: bool) -> str:
    if not items:
        return "مفهمتش الأكل — جرّب تكتبه أوضح، مثلاً: «بيضتين وكوباية لبن ورغيف عيش»."
    lines = [f"• {it.name_ar} ({_fmt_qty(it)}) ≈ {round(it.calories)} سعرة" for it in items]
    head = "سجّلت لك ✅:" if logged else "فهمت إنك أكلت:"
    tail = f"المجموع ≈ {round(total)} سعرة."
    if not logged:
        tail += " تأكّد من الأصناف وعدّل لو محتاج، وبعدين اضغط «سجّل الكل»."
    return head + "\n" + "\n".join(lines) + "\n" + tail


# ردّ جاهز (احتياطي) لمّا النص يبقى سؤال/طلب مش تسجيل أكل
_QUESTION_FALLBACK_REPLY = (
    "أنا هنا أساعدك! اكتبلي الأكل اللي أكلته (زي: بيضتين وعيش بلدي) وأنا أحسبهولك. "
    "لو عندك سؤال صحي اسأل وهجاوبك."
)


def _price_item(
    db: Session,
    name_ar: str,
    qty: float,
    unit_ar: str | None,
    grams: float,
    meal: Meal,
    ai_kcal_per_100: float | None = None,
) -> ParsedFoodItem:
    """يسعّر صنفاً واحداً بعدد جرامات معروف.

    الأولوية:
      1) تطابق مكتبة محكم (أدق + يشمل بروتين/نشويات/دهون) → سعرات المكتبة.
      2) لو الـ AI أعطى تقدير سعرات/100جم لهذا الصنف (من parse_meal_ai) نستخدمه مباشرة
         بدل المقدّر «الغبي».
      3) وإلا المقدّر المحلي (المدعوم بالـ AI أو الـ heuristic).
    """
    match = _match_library(db, name_ar)
    if match is not None:
        f = grams / 100.0
        return ParsedFoodItem(
            name_ar=match.name_ar, qty=qty, unit=unit_ar, grams=grams, meal=meal,
            calories=round(match.calories_per_100 * f), protein=round(match.protein * f, 1),
            carbs=round(match.carbs * f, 1), fat=round(match.fat * f, 1),
            confidence="high", source=FoodSource.library, matched_library_id=match.id,
            note_ar="من مكتبة الأكلات.",
        )

    # لا يوجد تطابق مكتبة واثق → لو الـ AI أعطى سعرات/100جم واقعية لهذا الصنف، نستخدمها
    if ai_kcal_per_100 is not None and ai_kcal_per_100 >= 0:
        f = grams / 100.0
        return ParsedFoodItem(
            name_ar=name_ar.strip() or name_ar, qty=qty, unit=unit_ar, grams=grams, meal=meal,
            calories=round(ai_kcal_per_100 * f), confidence="medium",
            source=FoodSource.estimated,
            note_ar="تقدير من المساعد الذكي — راجعه وعدّله لو محتاج.",
        )

    est = get_estimator().estimate(name_ar, grams)
    return ParsedFoodItem(
        name_ar=est.name_ar or name_ar, qty=qty, unit=unit_ar, grams=grams, meal=meal,
        calories=round(est.calories), protein=round(est.protein, 1),
        carbs=round(est.carbs, 1), fat=round(est.fat, 1),
        confidence=getattr(est, "confidence", "low"), source=FoodSource.estimated,
        note_ar=getattr(est, "note_ar", "تقدير تقريبي — راجع الرقم."),
    )


@router.post("/parse", response_model=ParseResponse)
@limiter.limit("30/minute")
def parse_meal(
    request: Request,
    payload: ParseRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """يفهم كلام حر عن الأكل، يطلّع الأصناف والسعرات (من المكتبة/المقدّر المحلي)، ويسجّلها عند التأكيد.

    لو الـ AI مفعّل: نخلّي Gemini يستخرج الأصناف والجرامات (والسعرات تتحسب محليًا)، ولو النص
    سؤال نرجع ردّ عام بدون أصناف. لو الـ AI متعطّل: نكشف الأسئلة بالـ heuristic ونرجع رد ودّي
    بدون تلفيق أصناف، وإلا نحلّل النص بالمحلّل المحلي زي الأول.
    """
    default_meal = payload.default_meal
    out: list[ParsedFoodItem] = []

    if settings.ai_enabled:
        ai = ai_assistant.parse_meal_ai(payload.text)
        # نثق في «ده سؤال» بس لو المحلّل المحلي وافق — يمنع موديل ضعيف إنه يصنّف أكل واضح
        # كسؤال ويطنّشه (السبب اللي كان بيخلّي «اكلت بيضتين» مايتسجّلش).
        if ai is not None and ai.get("is_question") and meal_parser.looks_like_question(payload.text):
            reply = ai_assistant.general_reply(payload.text) or _QUESTION_FALLBACK_REPLY
            return ParseResponse(
                items=[], total_calories=0, logged=False, logged_ids=[], reply_ar=reply,
            )
        if ai is not None and not ai.get("is_question"):
            # أصناف من الـ AI — نسعّرها: تطابق مكتبة واثق أولاً، وإلا تقدير الـ AI (kcal_per_100)
            for it in ai.get("items", [])[:25]:
                ai_kcal = it.get("kcal_per_100")
                ai_kcal_f = (
                    float(ai_kcal)
                    if isinstance(ai_kcal, (int, float)) and not isinstance(ai_kcal, bool)
                    else None
                )
                out.append(
                    _price_item(
                        db, it["name_ar"], 1.0, None, float(it["grams"]), default_meal,
                        ai_kcal_per_100=ai_kcal_f,
                    )
                )
        # لو لسه مفيش أصناف (الـ AI فشل/رجع فاضي/صنّفه سؤال غلط) → اكشف السؤال محليًا، وإلا
        # ارجع للمحلّل المحلي الحتمي بدل ما نطنّش أكل واضح.
        if not out:
            if meal_parser.looks_like_question(payload.text):
                return ParseResponse(
                    items=[], total_calories=0, logged=False, logged_ids=[],
                    reply_ar=_QUESTION_FALLBACK_REPLY,
                )
            out = _parse_heuristic_items(db, payload.text, default_meal.value)
    else:
        # مفيش AI — اكشف الأسئلة محليًا أولاً عشان مانلفّقش أصناف من سؤال
        if meal_parser.looks_like_question(payload.text):
            return ParseResponse(
                items=[], total_calories=0, logged=False, logged_ids=[],
                reply_ar=_QUESTION_FALLBACK_REPLY,
            )
        out = _parse_heuristic_items(db, payload.text, default_meal.value)

    total = round(sum(i.calories for i in out))
    logged_ids: list[int] = []
    logged = bool(payload.confirm and out)
    if logged:
        for it in out:
            row = FoodLogged(
                user_id=current_user.id, date=payload.date, meal=it.meal, name_ar=it.name_ar,
                amount=it.grams, calories=it.calories, protein=it.protein, carbs=it.carbs,
                fat=it.fat, source=it.source,
            )
            db.add(row)
            db.flush()
            logged_ids.append(row.id)
        db.commit()

    # ردّ ملخّص محلي للوجبة (بدون نداء AI إضافي) — التحليل والأرقام نفسها هي «الذكاء».
    # وفّرنا نداء المحادثة الإضافي عشان الحصة المجانية تكفي استخدام العيلة كله؛
    # الـ AI محجوز للتحليل الدقيق وللإجابة على الأسئلة (general_reply).
    reply = _build_reply(out, total, logged)

    return ParseResponse(
        items=out, total_calories=total, logged=logged,
        logged_ids=logged_ids, reply_ar=reply,
    )


def _parse_heuristic_items(db: Session, text: str, default_meal: str) -> list[ParsedFoodItem]:
    """المسار المحلي: يحلّل النص بالـ heuristic ويسعّر كل صنف عبر المكتبة/المقدّر."""
    # حد أقصى للأصناف في الطلب الواحد (يمنع إغراق قاعدة البيانات)
    raw_items = meal_parser.parse_text(text, default_meal)[:25]
    out: list[ParsedFoodItem] = []
    for raw in raw_items:
        match = _match_library(db, raw.name_ar)
        lib_hu = match.household_unit_ar if match else None
        lib_hg = match.household_grams if match else None
        grams = meal_parser.resolve_grams(raw.qty, raw.unit_ar, lib_hu, lib_hg, raw.name_ar)
        out.append(_price_item(db, raw.name_ar, raw.qty, raw.unit_ar, grams, Meal(raw.meal)))
    return out


# ---------- الباركود (ميزة مدفوعة) ----------
@router.get("/barcode/{code}", response_model=BarcodeOut)
def lookup_barcode(
    code: str,
    current_user: User = Depends(require_premium),
    db: Session = Depends(get_db),
):
    if not re.fullmatch(r"[0-9]{6,14}", code):
        raise HTTPException(status_code=422, detail="باركود غير صالح.")

    # 1) المكتبة المحلية أولاً (أسرع + يشمل منتجات المنطقة والمساهمات)
    lib = db.scalar(select(FoodLibrary).where(FoodLibrary.barcode == code).limit(1))
    if lib is not None:
        return BarcodeOut(
            barcode=code,
            name_ar=lib.name_ar,
            calories_per_100=lib.calories_per_100,
            protein=lib.protein,
            carbs=lib.carbs,
            fat=lib.fat,
            source="local",
        )

    # 2) Open Food Facts كاحتياطي
    result = barcode_svc.fetch_barcode(code)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="مالقيناش المنتج ده بالباركود. ضيف قيمه مرة وهنفتكره ليك المرة الجاية.",
        )
    return BarcodeOut(
        barcode=result.barcode,
        name_ar=result.name_ar,
        calories_per_100=result.calories_per_100,
        protein=result.protein,
        carbs=result.carbs,
        fat=result.fat,
        source="barcode",
    )


@router.post("/barcode", response_model=BarcodeOut, status_code=status.HTTP_201_CREATED)
def save_barcode(
    payload: BarcodeIn,
    current_user: User = Depends(require_premium),
    db: Session = Depends(get_db),
):
    """يحفظ منتجاً بالباركود في المكتبة (مساهمة) — فيُتعرَّف عليه بأي مسح لاحق."""
    if not re.fullmatch(r"[0-9]{6,14}", payload.barcode):
        raise HTTPException(status_code=422, detail="باركود غير صالح.")
    lib = db.scalar(select(FoodLibrary).where(FoodLibrary.barcode == payload.barcode).limit(1))
    if lib is None:
        lib = FoodLibrary(barcode=payload.barcode)
        db.add(lib)
    lib.name_ar = payload.name_ar.strip()
    lib.calories_per_100 = payload.calories_per_100
    lib.protein = payload.protein
    lib.carbs = payload.carbs
    lib.fat = payload.fat
    lib.household_unit_ar = payload.household_unit_ar
    lib.household_grams = payload.household_grams
    db.commit()
    db.refresh(lib)
    return BarcodeOut(
        barcode=payload.barcode,
        name_ar=lib.name_ar,
        calories_per_100=lib.calories_per_100,
        protein=lib.protein,
        carbs=lib.carbs,
        fat=lib.fat,
        source="contributed",
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
        if len(content) > 8 * 1024 * 1024:  # حد أقصى 8 ميجا للصورة
            raise HTTPException(status_code=413, detail="الصورة كبيرة جداً (الحد 8 ميجا).")
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


# ---------- قراءة ملصق التغذية من صورة بالرؤية الذكية (Gemini vision) ----------
@router.post("/label-image", response_model=LabelParseOut)
@limiter.limit("20/minute")
async def parse_label_image(
    request: Request,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
):
    """يقرأ صورة ملصق تغذية بالرؤية الذكية ويرجّع القيم لكل 100 جرام (نفس شكل /label).

    لو المساعد الذكي متعطّل أو فشل: نرجّع 200 بأصفار وملاحظة (تدهور رشيق، من غير 500 أبداً).
    """
    content_type = (file.content_type or "").lower()
    if not content_type.startswith("image/"):
        raise HTTPException(status_code=415, detail="لازم تبعت صورة (image/*).")

    content = await file.read()
    if not content:
        raise HTTPException(status_code=422, detail="الصورة فاضية.")
    if len(content) > 6 * 1024 * 1024:  # حد أقصى 6 ميجا للصورة
        raise HTTPException(status_code=413, detail="الصورة كبيرة جداً (الحد 6 ميجا).")

    values = ai_assistant.read_label_image_ai(content, mime=content_type)
    if values is None:
        return LabelParseOut(
            calories=0, protein=0, carbs=0, fat=0,
            basis_ar="لكل 100 جرام",
            note_ar=(
                "فعّل المساعد الذكي (مفتاح مجاني) عشان نقرا الملصق تلقائيًا، أو دخّل القيم يدويًا."
            ),
        )

    return LabelParseOut(
        calories=values["calories"], protein=values["protein"],
        carbs=values["carbs"], fat=values["fat"],
        basis_ar="لكل 100 جرام",
        note_ar="قرأنا الملصق بالذكاء الاصطناعي — راجع القيم وعدّلها قبل الحفظ.",
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
