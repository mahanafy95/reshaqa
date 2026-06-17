"""خدمة الباركود — تستعلم Open Food Facts وتُرجع القيم لكل 100 جرام.

دالة التحليل parse_off_product منفصلة وقابلة للاختبار بدون شبكة.
"""
from dataclasses import dataclass

import httpx

from ..config import settings

OFF_BASE = "https://world.openfoodfacts.org/api/v2/product"


@dataclass
class BarcodeResult:
    barcode: str
    name_ar: str
    calories_per_100: float
    protein: float
    carbs: float
    fat: float
    source: str = "barcode"


def parse_off_product(payload: dict, barcode: str) -> BarcodeResult | None:
    """يحوّل استجابة Open Food Facts إلى BarcodeResult (لكل 100 جرام)."""
    if not payload or payload.get("status") not in (1, "1"):
        return None
    product = payload.get("product") or {}
    nutr = product.get("nutriments") or {}

    cal = nutr.get("energy-kcal_100g")
    if cal is None:
        kj = nutr.get("energy_100g")
        cal = round(kj / 4.184, 1) if kj else None
    if cal is None:
        return None

    name = (
        product.get("product_name_ar")
        or product.get("product_name")
        or product.get("generic_name")
        or "منتج بالباركود"
    )
    return BarcodeResult(
        barcode=barcode,
        name_ar=str(name).strip(),
        calories_per_100=round(float(cal), 1),
        protein=round(float(nutr.get("proteins_100g") or 0), 1),
        carbs=round(float(nutr.get("carbohydrates_100g") or 0), 1),
        fat=round(float(nutr.get("fat_100g") or 0), 1),
    )


def fetch_barcode(barcode: str, timeout: float = 6.0) -> BarcodeResult | None:
    """يجلب منتجاً من Open Food Facts. يُرجع None عند عدم الوجود أو خطأ الشبكة."""
    url = f"{OFF_BASE}/{barcode}.json"
    headers = {"User-Agent": "Reshaqa/0.1 (nutrition app)"}
    try:
        resp = httpx.get(
            url,
            headers=headers,
            timeout=timeout,
            params={"fields": "product_name,product_name_ar,generic_name,nutriments"},
        )
        if resp.status_code != 200:
            return None
        return parse_off_product(resp.json(), barcode)
    except (httpx.HTTPError, ValueError):
        return None


# المزوّد قابل للتبديل مستقبلاً عبر settings.BARCODE_PROVIDER
def get_barcode_provider() -> str:
    return settings.BARCODE_PROVIDER
