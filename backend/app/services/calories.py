"""محرك حساب السعرات والماكروز — مع قواعد الأمان الصحي.

القواعد المطبّقة (مهمة):
- BMR بمعادلة Mifflin-St Jeor، ثم × معامل النشاط = TDEE.
- العجز للتخسيس: 15–20% من TDEE أو 500 سعرة (أيهما أقل)، ومعدل نزول أقصاه ~0.75 كجم/أسبوع.
- حد أدنى آمن: 1200 سعرة للنساء و1500 للرجال — لا يُسمح بأقل منه.
- منع الوزن المستهدف غير الصحي (أقل من BMI 18.5).
- وضع التثبيت تلقائياً عند الوصول للوزن المستهدف (سعرات المحافظة بلا عجز).
- بروتين 1.6–2.0 جم/كجم، والباقي يُقسَّم نشويات/دهون.
"""
from dataclasses import dataclass, field

from ..models.enums import ActivityLevel, Sex, TargetMode
from .body_metrics import HEALTHY_BMI_MIN, bmi, healthy_weight_range

# معاملات النشاط
ACTIVITY_FACTORS: dict[ActivityLevel, float] = {
    ActivityLevel.sedentary: 1.2,
    ActivityLevel.light: 1.375,
    ActivityLevel.moderate: 1.55,
    ActivityLevel.active: 1.725,
}

# الحد الأدنى الآمن للسعرات اليومية
SAFE_MIN_CALORIES: dict[Sex, int] = {
    Sex.female: 1200,
    Sex.male: 1500,
}

# طاقة 1 كجم من دهن الجسم (سعرة) ≈ 7700
KCAL_PER_KG_FAT = 7700.0

# الحدود الافتراضية للعجز
MAX_DEFICIT_KCAL = 500.0          # حد أقصى مطلق للعجز اليومي
DEFAULT_DEFICIT_PCT = 0.20        # 20% من TDEE (أعلى نطاق "المعتدل")
MAX_LOSS_RATE_KG_WEEK = 0.75      # أقصى معدل نزول مسموح

# حدود البروتين (جم/كجم)
PROTEIN_MIN_PER_KG = 1.6
PROTEIN_MAX_PER_KG = 2.0
# نسبة الدهون من السعرات
FAT_PCT_OF_CALORIES = 0.25
MIN_FAT_PCT = 0.20


def bmr_mifflin(sex: Sex, weight_kg: float, height_cm: float, age: int) -> float:
    """معادلة Mifflin-St Jeor لحساب معدل الأيض الأساسي (BMR)."""
    base = 10.0 * weight_kg + 6.25 * height_cm - 5.0 * age
    return base + 5.0 if sex == Sex.male else base - 161.0


def tdee(bmr: float, activity_level: ActivityLevel) -> float:
    """إجمالي الطاقة اليومية = BMR × معامل النشاط."""
    return bmr * ACTIVITY_FACTORS[activity_level]


def _deficit_from_rate(goal_rate_kg_week: float | None) -> float | None:
    """تحويل معدل النزول المطلوب (كجم/أسبوع) إلى عجز يومي (سعرة)."""
    if goal_rate_kg_week is None or goal_rate_kg_week <= 0:
        return None
    capped = min(goal_rate_kg_week, MAX_LOSS_RATE_KG_WEEK)
    return capped * KCAL_PER_KG_FAT / 7.0


def loss_deficit(tdee_value: float, goal_rate_kg_week: float | None = None) -> float:
    """يحسب العجز اليومي للتخسيس وفق قاعدة الأمان (أيهما أقل).

    deficit = min( 20% من TDEE , 500 سعرة [, العجز المقابل لمعدل النزول المطلوب] )
    """
    candidates = [DEFAULT_DEFICIT_PCT * tdee_value, MAX_DEFICIT_KCAL]
    rate_deficit = _deficit_from_rate(goal_rate_kg_week)
    if rate_deficit is not None:
        candidates.append(rate_deficit)
    return max(min(candidates), 0.0)


def determine_mode(current_weight_kg: float, goal_weight_kg: float | None) -> TargetMode:
    """وضع التثبيت عند الوصول للهدف (أو تجاوزه)، وإلا وضع التخسيس."""
    if goal_weight_kg is not None and current_weight_kg <= goal_weight_kg + 0.05:
        return TargetMode.maintain
    return TargetMode.loss


@dataclass
class GoalValidation:
    is_valid: bool
    healthy_min_kg: float
    healthy_max_kg: float
    suggested_goal_kg: float | None = None
    message_ar: str = ""


def validate_goal_weight(goal_weight_kg: float, height_cm: float) -> GoalValidation:
    """يتحقق أن الوزن المستهدف ضمن النطاق الصحي؛ يمنع ما هو أقل من الحد الصحي."""
    lo, hi = healthy_weight_range(height_cm)
    if goal_weight_kg < lo:
        return GoalValidation(
            is_valid=False,
            healthy_min_kg=lo,
            healthy_max_kg=hi,
            suggested_goal_kg=lo,
            message_ar=(
                f"الوزن المستهدف ({goal_weight_kg:g} كجم) تحت النطاق الصحي لطولك. "
                f"النطاق الصحي تقريباً من {lo:g} إلى {hi:g} كجم. "
                f"نقترح هدفاً لا يقل عن {lo:g} كجم — صحتك أهم 💚"
            ),
        )
    return GoalValidation(
        is_valid=True,
        healthy_min_kg=lo,
        healthy_max_kg=hi,
        message_ar="الوزن المستهدف ضمن النطاق الصحي 👍",
    )


@dataclass
class Macros:
    calories: float
    protein_g: float
    carbs_g: float
    fat_g: float


def split_macros(
    target_calories: float,
    weight_kg: float,
    protein_per_kg: float = 1.8,
) -> Macros:
    """يقسّم السعرات إلى ماكروز: بروتين حسب الوزن، دهون نسبة، والباقي نشويات.

    يضمن عدم سالبية أي عنصر حتى عند السعرات المنخفضة (يخفّض الدهون ثم البروتين عند الحاجة).
    """
    protein_per_kg = max(PROTEIN_MIN_PER_KG, min(PROTEIN_MAX_PER_KG, protein_per_kg))
    protein_g = protein_per_kg * weight_kg
    protein_cal = protein_g * 4.0

    fat_cal = target_calories * FAT_PCT_OF_CALORIES

    # لو البروتين + الدهون تجاوزا السعرات، خفّض الدهون لأدنى نسبة ثم خفّض البروتين عند اللزوم
    if protein_cal + fat_cal > target_calories:
        fat_cal = target_calories * MIN_FAT_PCT
        if protein_cal + fat_cal > target_calories:
            protein_cal = max(target_calories - fat_cal, 0.0)
            protein_g = protein_cal / 4.0

    fat_g = fat_cal / 9.0
    carbs_cal = max(target_calories - protein_cal - fat_cal, 0.0)
    carbs_g = carbs_cal / 4.0

    return Macros(
        calories=round(target_calories),
        protein_g=round(protein_g),
        carbs_g=round(carbs_g),
        fat_g=round(fat_g),
    )


@dataclass
class TargetResult:
    bmr: float
    tdee: float
    mode: TargetMode
    target_calories: float
    deficit_applied: float
    floored_to_safe_min: bool
    macros: Macros
    bmi: float
    messages_ar: list[str] = field(default_factory=list)


def compute_targets(
    *,
    sex: Sex,
    age: int,
    height_cm: float,
    weight_kg: float,
    activity_level: ActivityLevel,
    goal_weight_kg: float | None = None,
    goal_rate_kg_week: float | None = None,
    protein_per_kg: float = 1.8,
) -> TargetResult:
    """يحسب الأهداف اليومية كاملة مع تطبيق كل قواعد الأمان."""
    bmr_value = bmr_mifflin(sex, weight_kg, height_cm, age)
    tdee_value = tdee(bmr_value, activity_level)
    current_bmi = bmi(weight_kg, height_cm)
    messages: list[str] = []

    # بوابة أمان: لو الوزن الحالي تحت النطاق الصحي (BMI < 18.5) لا نطبّق أي عجز إطلاقاً —
    # نحوّل لوضع التثبيت مع تنبيه داعم (حتى لو لم يُحدّد وزن مستهدف).
    underweight = current_bmi < HEALTHY_BMI_MIN
    if underweight:
        mode = TargetMode.maintain
    else:
        mode = determine_mode(weight_kg, goal_weight_kg)

    if mode == TargetMode.maintain:
        target = tdee_value
        deficit = 0.0
        if underweight:
            messages.append(
                "وزنك الحالي تحت النطاق الصحي، فمش هنطبّق أي عجز — حسبنالك سعرات التثبيت. "
                "لو حابب تعدّل وزنك بصحة، يُفضّل استشارة مختص تغذية 💚"
            )
        else:
            messages.append("وصلت لوزنك المستهدف 🎉 حوّلناك لوضع التثبيت على سعرات المحافظة.")
    else:
        deficit = loss_deficit(tdee_value, goal_rate_kg_week)
        target = tdee_value - deficit

    # تطبيق الحد الأدنى الآمن
    safe_min = SAFE_MIN_CALORIES[sex]
    floored = False
    if target < safe_min:
        target = float(safe_min)
        floored = True
        messages.append(
            f"ثبّتنا هدفك عند الحد الأدنى الآمن ({safe_min} سعرة) للحفاظ على صحتك. "
            "النزول الصحي تدريجي ومستدام 💚"
        )

    macros = split_macros(target, weight_kg, protein_per_kg)

    return TargetResult(
        bmr=round(bmr_value, 1),
        tdee=round(tdee_value, 1),
        mode=mode,
        target_calories=round(target),
        deficit_applied=round(deficit),
        floored_to_safe_min=floored,
        macros=macros,
        bmi=round(current_bmi, 1),
        messages_ar=messages,
    )
