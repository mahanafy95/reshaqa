"use client";
import { useEffect, useState } from "react";
import { api, ApiError } from "@/lib/api";
import { Button, Card, Field, Select, Spinner } from "@/components/ui";
import { UNITS, toGrams, MILK_TYPES, milkType } from "@/lib/units";

const MEALS: Record<string, string> = { breakfast: "فطار", lunch: "غدا", dinner: "عشا", snack: "سناك" };
const today = () => new Date().toISOString().split("T")[0];

type Per100 = { cal: number; p: number; c: number; f: number };
type Ing = { name: string; qty: string; unit: string; per100: Per100; is_oil: boolean; lastEst: string; est: boolean };

const emptyIng = (): Ing => ({ name: "", qty: "100", unit: "g", per100: { cal: 0, p: 0, c: 0, f: 0 }, is_oil: false, lastEst: "", est: false });

export default function RecipesPage() {
  const [recipes, setRecipes] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [msg, setMsg] = useState<string | null>(null);

  const [editingId, setEditingId] = useState<number | null>(null);
  const [name, setName] = useState("");
  const [servings, setServings] = useState("1");
  const [ings, setIngs] = useState<Ing[]>([emptyIng()]);
  const [milkKey, setMilkKey] = useState("none");
  const [milkQty, setMilkQty] = useState("100");

  // تسجيل وصفة كأكل
  const [logFor, setLogFor] = useState<any | null>(null);
  const [logServings, setLogServings] = useState("1");
  const [logMeal, setLogMeal] = useState("breakfast");

  async function load() {
    try {
      setRecipes(await api.recipes());
    } finally {
      setLoading(false);
    }
  }
  useEffect(() => {
    load();
  }, []);

  function flash(m: string) {
    setMsg(m);
    setTimeout(() => setMsg(null), 4000);
  }

  function setIng(idx: number, patch: Partial<Ing>) {
    setIngs((prev) => prev.map((it, i) => (i === idx ? { ...it, ...patch } : it)));
  }

  async function estimateIng(idx: number) {
    const it = ings[idx];
    const term = it.name.trim();
    if (term.length < 2 || term === it.lastEst) return;
    setIng(idx, { est: true, lastEst: term });
    try {
      const r = await api.estimate(term, 100);
      setIng(idx, { per100: { cal: r.calories, p: r.protein, c: r.carbs, f: r.fat }, est: false });
    } catch {
      setIng(idx, { est: false });
    }
  }

  function ingGrams(it: Ing) {
    return toGrams(Number(it.qty) || 0, it.unit);
  }
  function ingCal(it: Ing) {
    return Math.round((it.per100.cal * ingGrams(it)) / 100);
  }

  function totals() {
    let cal = 0, p = 0, c = 0, f = 0;
    for (const it of ings) {
      if (!it.name.trim()) continue;
      const fct = ingGrams(it) / 100;
      cal += it.per100.cal * fct;
      p += it.per100.p * fct;
      c += it.per100.c * fct;
      f += it.per100.f * fct;
    }
    const m = milkType(milkKey);
    if (m.per100) {
      const fct = toGrams(Number(milkQty) || 0, "ml") / 100;
      cal += m.per100.cal * fct;
      p += m.per100.p * fct;
      c += m.per100.c * fct;
      f += m.per100.f * fct;
    }
    const s = Number(servings) || 1;
    return { cal: Math.round(cal), p: +p.toFixed(1), c: +c.toFixed(1), f: +f.toFixed(1), perCal: Math.round(cal / s) };
  }

  function resetForm() {
    setEditingId(null);
    setName("");
    setServings("1");
    setIngs([emptyIng()]);
    setMilkKey("none");
    setMilkQty("100");
  }

  function startEdit(r: any) {
    setEditingId(r.id);
    setName(r.name_ar);
    setServings(String(r.servings));
    setIngs(
      (r.ingredients || []).map((i: any) => {
        const fct = i.amount > 0 ? i.amount / 100 : 1;
        return {
          name: i.name_ar,
          qty: String(i.amount),
          unit: "g",
          per100: { cal: i.calories / fct, p: i.protein / fct, c: i.carbs / fct, f: i.fat / fct },
          is_oil: i.is_oil,
          lastEst: i.name_ar,
          est: false,
        } as Ing;
      })
    );
    setMilkKey("none");
    setMilkQty("100");
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  async function save() {
    const valid = ings.filter((it) => it.name.trim());
    const ingredients = valid.map((it) => ({
      name_ar: it.name.trim(),
      amount_g: Math.max(ingGrams(it), 0.1),
      is_oil: it.is_oil,
      per100_calories: Math.max(it.per100.cal, 0),
      per100_protein: Math.max(it.per100.p, 0),
      per100_carbs: Math.max(it.per100.c, 0),
      per100_fat: Math.max(it.per100.f, 0),
    }));
    const m = milkType(milkKey);
    if (m.per100) {
      ingredients.push({
        name_ar: m.label,
        amount_g: Math.max(toGrams(Number(milkQty) || 0, "ml"), 0.1),
        is_oil: false,
        per100_calories: m.per100.cal,
        per100_protein: m.per100.p,
        per100_carbs: m.per100.c,
        per100_fat: m.per100.f,
      });
    }
    if (!name.trim()) return flash("اكتب اسم الوصفة.");
    if (!ingredients.length) return flash("ضيف مكوّن واحد على الأقل.");
    const body = { name_ar: name.trim(), servings: Number(servings) || 1, ingredients };
    try {
      if (editingId) {
        await api.updateRecipe(editingId, body);
        flash("اتعدّلت الوصفة 👍");
      } else {
        await api.createRecipe(body);
        flash("اتحفظت الوصفة 👍");
      }
      resetForm();
      load();
    } catch (e) {
      flash(e instanceof ApiError ? e.message : "فشل حفظ الوصفة.");
    }
  }

  async function removeRecipe(r: any) {
    if (!window.confirm(`حذف وصفة "${r.name_ar}"؟`)) return;
    await api.deleteRecipe(r.id);
    if (editingId === r.id) resetForm();
    load();
  }

  async function doLog() {
    if (!logFor) return;
    try {
      await api.logRecipe(logFor.id, { date: today(), meal: logMeal, servings: Number(logServings) || 1 });
      flash(`اتسجّلت "${logFor.name_ar}" في ${MEALS[logMeal]} ✅ (تتحسب في سعرات يومك)`);
      setLogFor(null);
    } catch (e) {
      flash(e instanceof ApiError ? e.message : "فشل التسجيل.");
    }
  }

  const t = totals();

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-extrabold">الوصفات</h1>
      {msg && <div className="rounded-xl bg-teal/10 text-teal px-4 py-2.5 text-sm font-semibold">{msg}</div>}

      {/* بناء / تعديل وصفة */}
      <Card>
        <h2 className="font-bold text-lg mb-3">{editingId ? "✏️ تعديل وصفة" : "➕ وصفة جديدة"}</h2>
        <div className="grid grid-cols-2 gap-x-3">
          <Field label="اسم الوصفة" value={name} onChange={(e) => setName(e.target.value)} placeholder="مثلاً: قهوة بلبن" />
          <Field label="بتكفي كام نفر/كوب" type="number" inputMode="decimal" value={servings} onChange={(e) => setServings(e.target.value)} />
        </div>

        <div className="font-semibold text-sm text-muted mt-2 mb-1">المكوّنات (اكتب الاسم والسعرات تتجاب لوحدها)</div>
        <div className="space-y-3">
          {ings.map((it, idx) => (
            <div key={idx} className="rounded-xl border border-gray-100 p-3">
              <div className="flex gap-2 items-end">
                <div className="flex-1">
                  <Field
                    label={`مكوّن ${idx + 1}`}
                    value={it.name}
                    onChange={(e) => setIng(idx, { name: e.target.value })}
                    onBlur={() => estimateIng(idx)}
                    placeholder="مثلاً: بن، سكر، عسل…"
                    autoComplete="off"
                  />
                </div>
                {ings.length > 1 && (
                  <button type="button" onClick={() => setIngs(ings.filter((_, i) => i !== idx))} className="text-red-500 text-sm mb-3">
                    حذف
                  </button>
                )}
              </div>
              <div className="grid grid-cols-3 gap-x-2 items-end">
                <Field label="الكمية" type="number" inputMode="decimal" value={it.qty} onChange={(e) => setIng(idx, { qty: e.target.value })} />
                <Select label="الوحدة" value={it.unit} onChange={(e) => setIng(idx, { unit: e.target.value })}>
                  {UNITS.map((u) => (
                    <option key={u.key} value={u.key}>{u.label}</option>
                  ))}
                </Select>
                <div className="mb-3 text-center">
                  <div className="text-xs text-muted">سعرات</div>
                  <div className="font-bold text-teal">{it.est ? "…" : ingCal(it)}</div>
                </div>
              </div>
              <div className="flex items-center justify-between">
                <label className="flex items-center gap-2 text-sm">
                  <input type="checkbox" checked={it.is_oil} onChange={(e) => setIng(idx, { is_oil: e.target.checked })} />
                  <span>زيت/سمن (يتقسّم على الأنفار)</span>
                </label>
                <details>
                  <summary className="text-xs text-teal cursor-pointer">عدّل القيم لكل 100</summary>
                  <div className="grid grid-cols-4 gap-x-2 mt-1">
                    <Field label="سعرة" type="number" value={String(Math.round(it.per100.cal))} onChange={(e) => setIng(idx, { per100: { ...it.per100, cal: Number(e.target.value) || 0 } })} />
                    <Field label="بروتين" type="number" value={String(it.per100.p)} onChange={(e) => setIng(idx, { per100: { ...it.per100, p: Number(e.target.value) || 0 } })} />
                    <Field label="نشويات" type="number" value={String(it.per100.c)} onChange={(e) => setIng(idx, { per100: { ...it.per100, c: Number(e.target.value) || 0 } })} />
                    <Field label="دهون" type="number" value={String(it.per100.f)} onChange={(e) => setIng(idx, { per100: { ...it.per100, f: Number(e.target.value) || 0 } })} />
                  </div>
                </details>
              </div>
            </div>
          ))}
        </div>
        <button type="button" onClick={() => setIngs([...ings, emptyIng()])} className="text-teal font-semibold text-sm mt-2">
          + ضيف مكوّن
        </button>

        {/* خانة الحليب */}
        <div className="grid grid-cols-2 gap-x-3 mt-3 items-end border-t border-gray-100 pt-3">
          <Select label="🥛 الحليب" value={milkKey} onChange={(e) => setMilkKey(e.target.value)}>
            {MILK_TYPES.map((m) => (
              <option key={m.key} value={m.key}>{m.label}</option>
            ))}
          </Select>
          {milkKey !== "none" && (
            <Field label="كمية الحليب (مل)" type="number" inputMode="decimal" value={milkQty} onChange={(e) => setMilkQty(e.target.value)} />
          )}
        </div>

        {/* الملخص */}
        <div className="rounded-xl bg-teal/5 p-3 mt-3 grid grid-cols-2 gap-2 text-center">
          <div>
            <div className="text-2xl font-extrabold text-teal">{t.cal}</div>
            <div className="text-muted text-xs">سعرات الوصفة كلها</div>
          </div>
          <div>
            <div className="text-2xl font-extrabold text-teal">{t.perCal}</div>
            <div className="text-muted text-xs">سعرات النصيب الواحد</div>
          </div>
          <div className="col-span-2 text-muted text-xs">
            ماكروز كلية — بروتين {t.p} / نشويات {t.c} / دهون {t.f} جم
          </div>
        </div>

        <div className="flex gap-2 mt-3">
          {editingId && <Button variant="outline" onClick={resetForm} className="flex-1">إلغاء</Button>}
          <Button onClick={save} className="flex-1">{editingId ? "حفظ التعديل" : "احفظ الوصفة"}</Button>
        </div>
      </Card>

      {/* الوصفات المحفوظة */}
      <Card>
        <h2 className="font-bold text-lg mb-3">وصفاتي المحفوظة</h2>
        {loading ? (
          <Spinner />
        ) : recipes.length === 0 ? (
          <p className="text-muted text-center py-4">لسه مفيش وصفات. اعمل وصفة فوق واحفظها.</p>
        ) : (
          <div className="space-y-2">
            {recipes.map((r) => (
              <div key={r.id} className="rounded-xl border border-gray-100 p-3">
                <div className="flex justify-between items-start">
                  <div>
                    <div className="font-bold">{r.name_ar}</div>
                    <div className="text-muted text-sm">
                      النصيب: {r.per_serving_calories} سعرة • الكل: {r.total_calories} سعرة • {r.servings} نفر
                    </div>
                  </div>
                </div>
                <div className="flex gap-2 mt-2 flex-wrap">
                  <Button onClick={() => { setLogFor(r); setLogServings("1"); }} className="text-sm py-1.5">🍽️ سجّلها كأكل</Button>
                  <Button variant="outline" onClick={() => startEdit(r)} className="text-sm py-1.5">✏️ تعديل</Button>
                  <Button variant="danger" onClick={() => removeRecipe(r)} className="text-sm py-1.5">حذف</Button>
                </div>
              </div>
            ))}
          </div>
        )}
      </Card>

      {/* نافذة تسجيل وصفة كأكل */}
      {logFor && (
        <div className="fixed inset-0 bg-black/40 grid place-items-center p-4 z-20" onClick={() => setLogFor(null)}>
          <div className="bg-white rounded-2xl p-5 w-full max-w-sm" onClick={(e) => e.stopPropagation()}>
            <h3 className="font-bold text-lg mb-3">سجّل "{logFor.name_ar}" كأكل</h3>
            <Field label="أكلت كام نصيب؟" type="number" inputMode="decimal" value={logServings} onChange={(e) => setLogServings(e.target.value)} />
            <Select label="الوجبة" value={logMeal} onChange={(e) => setLogMeal(e.target.value)}>
              {Object.entries(MEALS).map(([k, v]) => (
                <option key={k} value={k}>{v}</option>
              ))}
            </Select>
            <div className="rounded-xl bg-teal/5 p-2 text-center text-sm mb-3">
              هيتحسب عليك ≈ <b className="text-teal">{Math.round(r_perCal(logFor) * (Number(logServings) || 1))}</b> سعرة
            </div>
            <div className="flex gap-2">
              <Button variant="outline" onClick={() => setLogFor(null)} className="flex-1">إلغاء</Button>
              <Button onClick={doLog} className="flex-1">سجّل في اليوم</Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function r_perCal(r: any): number {
  return r?.per_serving_calories || 0;
}
