"""أداة لمرة واحدة: استخراج عناصر مكتبة الأكلات من خرج الـ Workflow إلى JSON."""
import json
import sys
from pathlib import Path


def find_items(obj):
    if isinstance(obj, dict):
        if "items" in obj and isinstance(obj["items"], list):
            return obj["items"]
        for v in obj.values():
            r = find_items(v)
            if r is not None:
                return r
    elif isinstance(obj, list):
        for v in obj:
            r = find_items(v)
            if r is not None:
                return r
    return None


def main() -> int:
    src = Path(sys.argv[1])
    out = Path(sys.argv[2])
    data = json.loads(src.read_text(encoding="utf-8"))
    items = find_items(data)
    if not items:
        print("NO ITEMS FOUND")
        return 1
    # تنظيف وتوحيد الحقول
    clean = []
    seen = set()
    for it in items:
        name = str(it.get("name_ar", "")).strip()
        if not name or name in seen:
            continue
        cal = it.get("calories_per_100")
        if cal is None or cal < 0 or cal > 950:
            continue
        seen.add(name)
        clean.append({
            "name_ar": name,
            "calories_per_100": round(float(cal)),
            "protein": round(float(it.get("protein") or 0), 1),
            "carbs": round(float(it.get("carbs") or 0), 1),
            "fat": round(float(it.get("fat") or 0), 1),
            "region": it.get("region") if it.get("region") in ("eg", "sa", "generic") else "generic",
            "household_unit_ar": it.get("household_unit_ar") or None,
            "household_grams": it.get("household_grams") or None,
        })
    out.write_text(json.dumps(clean, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"wrote {len(clean)} items to {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
