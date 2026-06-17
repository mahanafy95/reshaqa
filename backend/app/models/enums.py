"""التعدادات (Enums) المستخدمة عبر النماذج — مخزّنة كنصوص (VARCHAR + CHECK) لتوافق Postgres/SQLite."""
import enum


class Sex(str, enum.Enum):
    male = "male"
    female = "female"


class ActivityLevel(str, enum.Enum):
    sedentary = "sedentary"   # خامل (1.2)
    light = "light"           # نشاط خفيف (1.375)
    moderate = "moderate"     # نشاط متوسط (1.55)
    active = "active"         # نشاط عالٍ (1.725)


class TargetMode(str, enum.Enum):
    loss = "loss"             # وضع التخسيس (عجز سعرات)
    maintain = "maintain"     # وضع التثبيت (سعرات المحافظة)


class Meal(str, enum.Enum):
    breakfast = "breakfast"
    lunch = "lunch"
    dinner = "dinner"
    snack = "snack"


class FoodSource(str, enum.Enum):
    manual = "manual"         # إدخال يدوي
    estimated = "estimated"   # تقدير تلقائي
    barcode = "barcode"       # من الباركود
    label = "label"           # من تصوير جدول التغذية (OCR)
    library = "library"       # من مكتبة الأكلات
    recipe = "recipe"         # من وصفة


class Region(str, enum.Enum):
    eg = "eg"                 # مصري
    sa = "sa"                 # سعودي
    generic = "generic"       # عام


class ActivitySource(str, enum.Enum):
    manual = "manual"
    huawei = "huawei"
    health_connect = "health_connect"


class FavoriteRefType(str, enum.Enum):
    library = "library"       # عنصر من مكتبة الأكلات
    recipe = "recipe"         # وصفة محفوظة
    custom = "custom"         # عنصر مخصّص محفوظ بقيمه
