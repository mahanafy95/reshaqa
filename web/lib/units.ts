// وحدات القياس — للمشروبات والمكوّنات. التحويل للجرام (الكثافة ~1 للسوائل).
export type Unit = { key: string; label: string; factor: number };

export const UNITS: Unit[] = [
  { key: "g", label: "جرام", factor: 1 },
  { key: "ml", label: "مل", factor: 1 },
  { key: "tsp", label: "معلقة صغيرة", factor: 5 },
  { key: "tbsp", label: "معلقة كبيرة", factor: 15 },
  { key: "cup", label: "كوب (~240مل)", factor: 240 },
];

export const unitFactor = (k: string) => UNITS.find((u) => u.key === k)?.factor ?? 1;
export const unitLabel = (k: string) => UNITS.find((u) => u.key === k)?.label ?? "جرام";
export const toGrams = (qty: number, unit: string) => (Number(qty) || 0) * unitFactor(unit);

/** وصف مقروء للكمية بوحدتها، مثلاً "٢ معلقة كبيرة" أو "٢٠٠ مل". */
export function unitText(qty: number, unit: string): string {
  if (unit === "g") return `${qty} جم`;
  return `${qty} ${unitLabel(unit)}`;
}

// أنواع الحليب الجاهزة (لكل 100 مل) — لخانة "بحليب/بدون" في الوصفات والمشروبات.
export type MilkType = { key: string; label: string; per100?: { cal: number; p: number; c: number; f: number } };
export const MILK_TYPES: MilkType[] = [
  { key: "none", label: "بدون حليب" },
  { key: "full", label: "حليب كامل الدسم", per100: { cal: 61, p: 3.2, c: 4.8, f: 3.3 } },
  { key: "semi", label: "حليب نص دسم", per100: { cal: 47, p: 3.3, c: 4.8, f: 1.8 } },
  { key: "skim", label: "حليب خالي الدسم", per100: { cal: 34, p: 3.4, c: 5.0, f: 0.1 } },
];
export const milkType = (k: string) => MILK_TYPES.find((m) => m.key === k) ?? MILK_TYPES[0];
