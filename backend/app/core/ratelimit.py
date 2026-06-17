"""تحديد معدّل الطلبات (Rate limiting) — يحمي نقاط المصادقة من التخمين وإغراق التسجيل.

يُفعَّل فقط في الإنتاج (APP_ENV=production) كي لا يعطّل الاختبارات/التطوير المحلي.
التخزين في الذاكرة (افتراضي) — مناسب لنسخة Render المجانية ذات النسخة الواحدة، بلا أي تكلفة.
"""
import warnings

from slowapi import Limiter
from slowapi.util import get_remote_address
from starlette.requests import Request

from ..config import settings


def _client_key(request: Request) -> str:
    """يحدّد عميل الطلب — يقرأ X-Forwarded-For خلف بروكسي Render ليحسب لكل IP فعلي."""
    xff = request.headers.get("x-forwarded-for")
    if xff:
        return xff.split(",")[0].strip()
    return get_remote_address(request)


with warnings.catch_warnings():
    # نتجاهل تحذير "Config file '' not found" — متعمَّد: لا نقرأ .env عبر slowapi
    # (إعداداتنا تُقرأ في config.py)، وهذا يتفادى أيضاً خطأ ترميز cp1252 على ويندوز.
    warnings.simplefilter("ignore", UserWarning)
    limiter = Limiter(
        key_func=_client_key,
        enabled=(settings.APP_ENV == "production"),
        config_filename="",
    )
