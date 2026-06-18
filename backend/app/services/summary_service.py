"""بناء الملخص اليومي وحالة الماكروز — بنبرة داعمة دائماً وبدون لوم."""
from datetime import date as date_type

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models.enums import Meal, TargetMode
from ..models.food import FoodLogged
from ..models.profile import Profile
from . import targets_service

TOLERANCE = 0.10  # ±10% يُعتبر "مظبوط"


def _status_calories(target: float, eaten: float, mode: TargetMode) -> tuple[str, str]:
    over = eaten > target * (1 + TOLERANCE)
    under = eaten < target * (1 - TOLERANCE)
    if mode == TargetMode.gain:
        # في الزيادة: الأكل الأكثر مطلوب — التحت-هدف هو اللي محتاج تذكير
        if under:
            return "قليل", "لسه قدامك سعرات من هدف الزيادة — كمّل أكلك (وبروتينك) عشان نكسب عضل 💪"
        if over:
            return "كتير", "زوّدت شوية عن هدف الزيادة، خلّيها تدريجية عشان تكسب عضل أكتر من الدهون 🙂"
        return "مظبوط", "ماشي على هدف الزيادة بظبط 👏"
    # تخسيس/تثبيت
    if over:
        return "كتير", "زوّدت شوية عن هدفك النهاردة، وده بيحصل للكل! بكرة يوم جديد واحنا ماشيين صح 💚"
    if under:
        return "قليل", "لسه قدامك سعرات من هدفك — متنساش تاكل كفايتك عشان طاقتك تفضل كويسة 🙂"
    return "مظبوط", "ماشي على هدفك بظبط، تمام التمام 👏"


def _status_protein(target: float, eaten: float) -> tuple[str, str]:
    if eaten >= target * (1 - TOLERANCE):
        return "مظبوط", "بروتينك ممتاز النهاردة 💪"
    if eaten >= target * 0.6:
        return "قليل", "قرّبت من هدف البروتين — زوّده شوية (بيض/دجاج/زبادي) 🙂"
    return "قليل", "البروتين لسه قليل — حاول تزوّده، بيحافظ على عضلاتك وبيشبّع 💪"


def _status_generic(name: str, target: float, eaten: float) -> tuple[str, str]:
    if eaten > target * (1 + TOLERANCE):
        return "كتير", f"ال{name} زادت شوية عن المعتاد، عادي — وازن في باقي اليوم 🙂"
    if eaten < target * (1 - TOLERANCE):
        return "قليل", f"ال{name} لسه أقل من هدفك، عندك مساحة 👍"
    return "مظبوط", f"ال{name} مظبوطة 👏"


def build_summary(db: Session, user_id: int, profile: Profile, day: date_type) -> dict:
    """يحسب ملخص اليوم: المتاكل مقابل الهدف + حالة الماكروز + رسائل داعمة."""
    result, _cw, _pl = targets_service.compute_for_user(db, user_id, profile)
    target = result.macros

    logs = db.scalars(
        select(FoodLogged).where(FoodLogged.user_id == user_id, FoodLogged.date == day)
    ).all()

    eaten_cal = sum(x.calories for x in logs)
    eaten_p = sum(x.protein for x in logs)
    eaten_c = sum(x.carbs for x in logs)
    eaten_f = sum(x.fat for x in logs)

    # تفصيل الوجبات
    meal_totals: dict[Meal, dict] = {}
    for x in logs:
        m = meal_totals.setdefault(
            x.meal, {"calories": 0.0, "protein": 0.0, "carbs": 0.0, "fat": 0.0}
        )
        m["calories"] += x.calories
        m["protein"] += x.protein
        m["carbs"] += x.carbs
        m["fat"] += x.fat

    cal_status, cal_msg = _status_calories(target.calories, eaten_cal, result.mode)
    p_status, p_msg = _status_protein(target.protein_g, eaten_p)
    c_status, c_msg = _status_generic("نشويات", target.carbs_g, eaten_c)
    f_status, f_msg = _status_generic("دهون", target.fat_g, eaten_f)

    remaining = target.calories - eaten_cal
    percent = int(round(eaten_cal / target.calories * 100)) if target.calories else 0

    is_gain = result.mode == TargetMode.gain
    if cal_status == "مظبوط":
        encouragement = "يوم متوازن وجميل، كمّل كده 🌟"
    elif cal_status == "قليل":
        encouragement = (
            "محتاج تاكل أكتر شوية عشان نوصل لهدف الزيادة 💪"
            if is_gain
            else "بداية كويسة، خد راحتك وكمّل يومك بصحة 🙂"
        )
    else:
        encouragement = (
            "زوّدت كويس النهاردة 👍 خلّي الزيادة تدريجية ومتوازنة"
            if is_gain
            else "مفيش حاجة اسمها يوم وحش — المهم الاستمرار، وإنت ماشي صح 💚"
        )

    return {
        "date": day,
        "mode": result.mode,
        "target_calories": target.calories,
        "eaten_calories": round(eaten_cal),
        "remaining_calories": round(remaining),
        "percent_of_target": percent,
        "calories_status": {
            "name_ar": "سعرات", "target": target.calories, "eaten": round(eaten_cal),
            "remaining": round(remaining), "status": cal_status, "message_ar": cal_msg,
        },
        "macros": [
            {"name_ar": "بروتين", "target": target.protein_g, "eaten": round(eaten_p, 1),
             "remaining": round(target.protein_g - eaten_p, 1), "status": p_status, "message_ar": p_msg},
            {"name_ar": "نشويات", "target": target.carbs_g, "eaten": round(eaten_c, 1),
             "remaining": round(target.carbs_g - eaten_c, 1), "status": c_status, "message_ar": c_msg},
            {"name_ar": "دهون", "target": target.fat_g, "eaten": round(eaten_f, 1),
             "remaining": round(target.fat_g - eaten_f, 1), "status": f_status, "message_ar": f_msg},
        ],
        "meals": [
            {"meal": m, "calories": round(v["calories"]), "protein": round(v["protein"], 1),
             "carbs": round(v["carbs"], 1), "fat": round(v["fat"], 1)}
            for m, v in meal_totals.items()
        ],
        "encouragement_ar": encouragement,
    }
