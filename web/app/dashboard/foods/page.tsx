"use client";
import { useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";
import { Button, Card, Field, Select, Spinner } from "@/components/ui";
import { UNITS, toGrams, unitText, SUGAR_TYPES, sugarType, SUGAR_UNITS, sugarUnitGrams } from "@/lib/units";
import MealChat from "@/components/MealChat";

const MEALS: Record<string, string> = { breakfast: "فطار", lunch: "غدا", dinner: "عشا", snack: "سناك" };
const today = () => new Date().toISOString().split("T")[0];
type Per100 = { cal: number; p: number; c: number; f: number };

export default function FoodsPage() {
  const [meal, setMeal] = useState("lunch");
  const [logs, setLogs] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [results, setResults] = useState<any[]>([]);

  const [name, setName] = useState("");
  const [unit, setUnit] = useState("g");
  const [qty, setQty] = useState("100");
  const [cal, setCal] = useState("");
  const [protein, setProtein] = useState("");
  const [carbs, setCarbs] = useState("");
  const [fat, setFat] = useState("");

  // السكر المُضاف (للمشروبات)
  const [sugarKey, setSugarKey] = useState("none");
  const [sugarQty, setSugarQty] = useState("1");
  const [sugarUnit, setSugarUnit] = useState("tsp");

  const [per100, setPer100] = useState<Per100 | null>(null);
  const [manual, setManual] = useState(false); // المستخدم عدّل الأرقام بإيده
  const [estimating, setEstimating] = useState(false);
  const [note, setNote] = useState<string | null>(null);
  const [msg, setMsg] = useState<string | null>(null);
  const lastEstimated = useRef("");

  const grams = toGrams(Number(qty) || 0, unit);
  const sugarG = sugarKey === "none" ? 0 : (Number(sugarQty) || 0) * sugarUnitGrams(sugarUnit);
  const sugarCal = Math.round(sugarG * sugarType(sugarKey).calPerG);
  const sugarCarbs = +(sugarG * sugarType(sugarKey).carbPerG).toFixed(1);
  const totalCal = (Number(cal) || 0) + sugarCal;

  async function load() {
    setLogs(await api.foods(today()));
    setLoading(false);
  }
  useEffect(() => {
    load();
  }, []);

  // بحث المكتبة + جلب السعرات تلقائياً أول ما تكتب الصنف
  useEffect(() => {
    const term = name.trim();
    const t = setTimeout(async () => {
      if (term.length < 2) {
        setResults([]);
        return;
      }
      try {
        setResults(await api.librarySearch(term));
      } catch {}
      if (term !== lastEstimated.current) {
        lastEstimated.current = term;
        setEstimating(true);
        try {
          const r = await api.estimate(term, 100); // قيم لكل 100
          setPer100({ cal: r.calories, p: r.protein, c: r.carbs, f: r.fat });
          setManual(false);
          setNote(r.note_ar || null);
        } catch {
        } finally {
          setEstimating(false);
        }
      }
    }, 450);
    return () => clearTimeout(t);
  }, [name]);

  // اشتقاق السعرات من قيم الـ100 حسب الكمية والوحدة (طالما المستخدم ما عدّلش بإيده)
  useEffect(() => {
    if (per100 && !manual) {
      const f = grams / 100;
      setCal(String(Math.round(per100.cal * f)));
      setProtein((per100.p * f).toFixed(1));
      setCarbs((per100.c * f).toFixed(1));
      setFat((per100.f * f).toFixed(1));
    }
  }, [per100, grams, manual]);

  function pickLibrary(item: any) {
    setName(item.name_ar);
    lastEstimated.current = item.name_ar; // ما نعيدش التقدير
    setUnit("g");
    setQty(String(item.household_grams || 100));
    setPer100({ cal: item.calories_per_100, p: item.protein, c: item.carbs, f: item.fat });
    setManual(false);
    setNote("من مكتبة الأكلات.");
    setResults([]);
  }

  function editMacro(setter: (v: string) => void, v: string) {
    setManual(true); // وقف الاشتقاق التلقائي — المستخدم بيعدّل
    setter(v);
  }

  function reset() {
    setName("");
    setUnit("g");
    setQty("100");
    setCal("");
    setProtein("");
    setCarbs("");
    setFat("");
    setPer100(null);
    setManual(false);
    setNote(null);
    setSugarKey("none");
    setSugarQty("1");
    setSugarUnit("tsp");
    lastEstimated.current = "";
  }

  async function add(e: React.FormEvent) {
    e.preventDefault();
    if (!name.trim()) return;
    let displayName = unit === "g" ? name.trim() : `${name.trim()} (${unitText(Number(qty) || 0, unit)})`;
    if (sugarKey !== "none") {
      const su = SUGAR_UNITS.find((u) => u.key === sugarUnit);
      displayName += ` + ${sugarType(sugarKey).label} (${sugarQty} ${su?.key === "g" ? "جم" : su?.label.split(" ")[0] + " " + (su?.label.split(" ")[1] || "")})`;
    }
    await api.addFood({
      date: today(),
      meal,
      name_ar: displayName,
      amount: Math.round((grams + sugarG) * 10) / 10 || 1,
      calories: totalCal,
      protein: Number(protein) || 0,
      carbs: +((Number(carbs) || 0) + sugarCarbs).toFixed(1),
      fat: Number(fat) || 0,
      source: "manual",
    });
    reset();
    setMsg("اتسجّل 👍");
    load();
  }

  async function remove(id: number) {
    await api.deleteFood(id);
    load();
  }

  const total = logs.reduce((s, x) => s + x.calories, 0);

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-extrabold">تسجيل الأكل والمشروبات</h1>

      <MealChat defaultMeal={meal} todayTotal={total} onLogged={load} />

      <Card>
        <div className="flex gap-2 flex-wrap mb-4">
          {Object.entries(MEALS).map(([k, v]) => (
            <button
              key={k}
              onClick={() => setMeal(k)}
              className={`rounded-full px-4 py-1.5 text-sm font-semibold ${meal === k ? "bg-teal text-white" : "bg-gray-100 text-muted"}`}
            >
              {v}
            </button>
          ))}
        </div>

        <form onSubmit={add}>
          <div className="relative">
            <Field
              label="اسم الصنف (اكتبه والسعرات تتجاب لوحدها)"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="مثلاً: قهوة بلبن، رز، تفاح…"
              autoComplete="off"
            />
            {estimating && <span className="absolute left-3 top-9 text-xs text-muted">بنحسب…</span>}
            {results.length > 0 && (
              <div className="absolute z-10 left-0 right-0 bg-white border border-gray-100 rounded-xl max-h-52 overflow-auto shadow-lg">
                {results.map((r) => (
                  <button
                    type="button"
                    key={r.id}
                    onClick={() => pickLibrary(r)}
                    className="w-full text-right px-4 py-2 hover:bg-gray-50 flex justify-between"
                  >
                    <span>{r.name_ar}</span>
                    <span className="text-muted text-sm">{r.calories_per_100} /100</span>
                  </button>
                ))}
              </div>
            )}
          </div>

          <div className="grid grid-cols-2 gap-x-3">
            <Field label="الكمية" type="number" inputMode="decimal" value={qty} onChange={(e) => setQty(e.target.value)} />
            <Select label="الوحدة" value={unit} onChange={(e) => setUnit(e.target.value)}>
              {UNITS.map((u) => (
                <option key={u.key} value={u.key}>
                  {u.label}
                </option>
              ))}
            </Select>
          </div>

          <div className="rounded-xl border border-gray-100 p-3 mb-3">
            <div className="grid grid-cols-2 gap-x-3 items-end">
              <Select label="🍬 سكر/مُحلّي المشروب" value={sugarKey} onChange={(e) => setSugarKey(e.target.value)}>
                {SUGAR_TYPES.map((s) => (
                  <option key={s.key} value={s.key}>{s.label}</option>
                ))}
              </Select>
              {sugarKey !== "none" && (
                <div className="grid grid-cols-2 gap-x-2">
                  <Field label="عدد" type="number" inputMode="decimal" value={sugarQty} onChange={(e) => setSugarQty(e.target.value)} />
                  <Select label="الوحدة" value={sugarUnit} onChange={(e) => setSugarUnit(e.target.value)}>
                    {SUGAR_UNITS.map((u) => (
                      <option key={u.key} value={u.key}>{u.label}</option>
                    ))}
                  </Select>
                </div>
              )}
            </div>
            {sugarKey !== "none" && (
              <p className="text-muted text-xs mt-1">
                {sugarCal > 0 ? `السكر بيضيف ${sugarCal} سعرة` : "استيفيا — صفر سعرات 👍"}
              </p>
            )}
          </div>

          <div className="rounded-xl bg-teal/5 p-3 mb-3 text-center">
            <div className="text-3xl font-extrabold text-teal">{totalCal || 0}</div>
            <div className="text-muted text-sm">
              سعرة لـ {unitText(Number(qty) || 0, unit)}
              {unit !== "g" && grams ? ` (≈ ${Math.round(grams)} جم)` : ""}
              {sugarCal > 0 ? ` + ${sugarCal} سكر` : ""}
            </div>
          </div>

          <details className="mb-3">
            <summary className="text-sm text-teal cursor-pointer">تعديل التفاصيل يدوياً (سعرات وماكروز)</summary>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-x-3 mt-2">
              <Field label="سعرات" type="number" value={cal} onChange={(e) => editMacro(setCal, e.target.value)} />
              <Field label="بروتين" type="number" value={protein} onChange={(e) => editMacro(setProtein, e.target.value)} />
              <Field label="نشويات" type="number" value={carbs} onChange={(e) => editMacro(setCarbs, e.target.value)} />
              <Field label="دهون" type="number" value={fat} onChange={(e) => editMacro(setFat, e.target.value)} />
            </div>
          </details>

          {note && <p className="text-muted text-xs mb-2">{note}</p>}
          {msg && <p className="text-teal text-sm mb-2">{msg}</p>}
          <Button type="submit" className="w-full">أضف للوجبة</Button>
        </form>
      </Card>

      <Card>
        <div className="flex justify-between mb-3">
          <h2 className="font-bold text-lg">أكل النهاردة</h2>
          <span className="text-teal font-bold">{Math.round(total)} سعرة</span>
        </div>
        {loading ? (
          <Spinner />
        ) : logs.length === 0 ? (
          <p className="text-muted text-center py-4">لسه مسجّلتش حاجة النهاردة.</p>
        ) : (
          <div className="space-y-1">
            {logs.map((l) => (
              <div key={l.id} className="flex items-center justify-between py-2 border-b border-gray-50 last:border-0">
                <div>
                  <div className="font-semibold">{l.name_ar}</div>
                  <div className="text-muted text-sm">
                    {MEALS[l.meal]} • {Math.round(l.calories)} سعرة
                    {l.protein ? ` • ب${Math.round(l.protein)} ك${Math.round(l.carbs)} د${Math.round(l.fat)}` : ""}
                  </div>
                </div>
                <button onClick={() => remove(l.id)} className="text-red-500 text-sm">حذف</button>
              </div>
            ))}
          </div>
        )}
      </Card>
    </div>
  );
}
