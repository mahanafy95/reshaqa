"""مؤشرات الجسم — BMI، النطاق الصحي، وتقدير نسبة الدهون.

كل القيم تقديرية للتوعية وليست تشخيصاً طبياً.
"""
from dataclasses import dataclass

from ..models.enums import Sex

# حدود BMI الصحية (منظمة الصحة العالمية).
# نستخدم 25.0 كحدّ واحد متّسق بين التصنيف ونطاق الوزن الصحي حتى لا تظهر فجوة
# في النطاق [24.9, 25.0) (الطبيعي = [18.5, 25.0)، وزيادة الوزن تبدأ من 25.0).
HEALTHY_BMI_MIN = 18.5
HEALTHY_BMI_MAX = 25.0
# عتبة "فوق الوزن الصحي" — نفس حدّ النطاق الصحي الأعلى (بلا فجوة)
OVERWEIGHT_BMI_MIN = HEALTHY_BMI_MAX

# تصنيفات حالة الوزن (تُستخدم لاختيار البرنامج: زيادة/تثبيت/تخسيس)
STATUS_UNDERWEIGHT = "underweight"
STATUS_NORMAL = "normal"
STATUS_OVERWEIGHT = "overweight"

# الـ BMI المستهدف المقترح لكل حالة (داخل النطاق الصحي بمسافة مريحة، مش على الحافة)
TARGET_BMI_FOR_GAIN = 20.0   # لمن هو تحت النطاق الصحي
TARGET_BMI_FOR_LOSS = 24.0   # لمن هو فوق النطاق الصحي


def bmi(weight_kg: float, height_cm: float) -> float:
    """مؤشر كتلة الجسم = الوزن(كجم) / (الطول بالمتر)²."""
    if height_cm <= 0:
        raise ValueError("الطول يجب أن يكون أكبر من صفر")
    h_m = height_cm / 100.0
    return weight_kg / (h_m * h_m)


def weight_at_bmi(target_bmi: float, height_cm: float) -> float:
    """الوزن (كجم) المقابل لـ BMI معيّن عند طول معيّن."""
    h_m = height_cm / 100.0
    return round(target_bmi * h_m * h_m, 1)


def weight_status(bmi_value: float) -> str:
    """تصنيف حالة الوزن: تحت / ضمن / فوق النطاق الصحي."""
    if bmi_value < HEALTHY_BMI_MIN:
        return STATUS_UNDERWEIGHT
    if bmi_value >= OVERWEIGHT_BMI_MIN:
        return STATUS_OVERWEIGHT
    return STATUS_NORMAL


def recommended_goal_weight(weight_kg: float, height_cm: float) -> float | None:
    """الوزن المستهدف المقترح حسب الحالة:

    - تحت النطاق الصحي → وزن مريح داخل الطبيعي (BMI 20) ← زيادة.
    - فوق النطاق الصحي → أعلى الطبيعي بمسافة مريحة (BMI 24) ← تخسيس.
    - ضمن الطبيعي → None (الهدف هو التثبيت على الوزن الحالي).
    """
    status = weight_status(bmi(weight_kg, height_cm))
    if status == STATUS_UNDERWEIGHT:
        return weight_at_bmi(TARGET_BMI_FOR_GAIN, height_cm)
    if status == STATUS_OVERWEIGHT:
        return weight_at_bmi(TARGET_BMI_FOR_LOSS, height_cm)
    return None


def bmi_category_ar(bmi_value: float) -> str:
    """تصنيف BMI بنبرة داعمة وغير حاكمة (يُعرض دائماً بجانب النطاق الصحي)."""
    if bmi_value < 18.5:
        return "تحت النطاق الصحي"
    if bmi_value < 25:
        return "ضمن الوزن الصحي 👍"
    if bmi_value < 30:
        return "فوق النطاق الصحي شوية"
    return "فوق النطاق الصحي"


def healthy_weight_range(height_cm: float) -> tuple[float, float]:
    """نطاق الوزن الصحي (كجم) المقابل لـ BMI 18.5–24.9 حسب الطول."""
    h_m = height_cm / 100.0
    lo = HEALTHY_BMI_MIN * h_m * h_m
    hi = HEALTHY_BMI_MAX * h_m * h_m
    return round(lo, 1), round(hi, 1)


def body_fat_deurenberg(bmi_value: float, age: int, sex: Sex) -> float:
    """تقدير نسبة الدهون بمعادلة Deurenberg (تحتاج BMI والعمر والجنس فقط)."""
    sex_factor = 1 if sex == Sex.male else 0
    bf = 1.20 * bmi_value + 0.23 * age - 10.8 * sex_factor - 5.4
    # تقييد ضمن نطاق فسيولوجي معقول لتفادي قيم غير منطقية عند الأطراف
    return round(min(max(bf, 2.0), 70.0), 1)


def body_fat_us_navy(
    sex: Sex,
    height_cm: float,
    waist_cm: float,
    neck_cm: float,
    hip_cm: float | None = None,
) -> float | None:
    """تقدير نسبة الدهون بصيغة البحرية الأمريكية (US Navy).

    تحتاج محيط الخصر والرقبة والطول (وللنساء محيط الورك أيضاً).
    تُرجع None لو المعطيات غير كافية أو خارج النطاق المنطقي.
    """
    import math

    try:
        if sex == Sex.male:
            if waist_cm <= neck_cm:
                return None
            bf = (
                495
                / (
                    1.0324
                    - 0.19077 * math.log10(waist_cm - neck_cm)
                    + 0.15456 * math.log10(height_cm)
                )
                - 450
            )
        else:
            if hip_cm is None or (waist_cm + hip_cm) <= neck_cm:
                return None
            bf = (
                495
                / (
                    1.29579
                    - 0.35004 * math.log10(waist_cm + hip_cm - neck_cm)
                    + 0.22100 * math.log10(height_cm)
                )
                - 450
            )
    except (ValueError, ZeroDivisionError):
        return None
    if bf <= 0 or bf >= 70:
        return None
    return round(bf, 1)


@dataclass
class BodyComposition:
    """تركيب الجسم التقريبي بناءً على الوزن ونسبة الدهون."""

    fat_mass_kg: float
    lean_mass_kg: float
    body_fat_pct: float


def body_composition(weight_kg: float, body_fat_pct: float) -> BodyComposition:
    fat = weight_kg * body_fat_pct / 100.0
    return BodyComposition(
        fat_mass_kg=round(fat, 1),
        lean_mass_kg=round(weight_kg - fat, 1),
        body_fat_pct=round(body_fat_pct, 1),
    )
