"use client";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { Button, Card, Field, Select, Spinner } from "@/components/ui";

const MEALS: Record<string, string> = { breakfast: "فطار", lunch: "غدا", dinner: "عشا", snack: "سناك" };
const today = () => new Date().toISOString().split("T")[0];

export default function FoodsPage() {
  const [meal, setMeal] = useState("lunch");
  const [logs, setLogs] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [q, setQ] = useState("");
  const [results, setResults] = useState<any[]>([]);
  const [form, setForm] = useState({ name_ar: "", amount: "100", calories: "", protein: "", carbs: "", fat: "" });
  const [msg, setMsg] = useState<string | null>(null);

  async function load() {
    setLogs(await api.foods(today()));
    setLoading(false);
  }
  useEffect(() => {
    load();
  }, []);

  useEffect(() => {
    const t = setTimeout(async () => {
      if (q.trim().length < 2) return setResults([]);
      try {
        setResults(await api.librarySearch(q.trim()));
      } catch {}
    }, 300);
    return () => clearTimeout(t);
  }, [q]);

  const set = (k: string, v: string) => setForm({ ...form, [k]: v });

  function pickLibrary(item: any) {
    const grams = item.household_grams || 100;
    const f = grams / 100;
    setForm({
      name_ar: item.name_ar,
      amount: String(grams),
      calories: String(Math.round(item.calories_per_100 * f)),
      protein: (item.protein * f).toFixed(1),
      carbs: (item.carbs * f).toFixed(1),
      fat: (item.fat * f).toFixed(1),
    });
    setResults([]);
    setQ("");
  }

  async function estimate() {
    if (!form.name_ar.trim()) return;
    const r = await api.estimate(form.name_ar.trim(), Number(form.amount) || 100);
    setForm({
      ...form,
      calories: String(Math.round(r.calories)),
      protein: String(r.protein),
      carbs: String(r.carbs),
      fat: String(r.fat),
    });
    setMsg(r.note_ar);
  }

  async function add(e: React.FormEvent) {
    e.preventDefault();
    if (!form.name_ar.trim()) return;
    await api.addFood({
      date: today(),
      meal,
      name_ar: form.name_ar.trim(),
      amount: Number(form.amount) || 100,
      calories: Number(form.calories) || 0,
      protein: Number(form.protein) || 0,
      carbs: Number(form.carbs) || 0,
      fat: Number(form.fat) || 0,
      source: "manual",
    });
    setForm({ name_ar: "", amount: "100", calories: "", protein: "", carbs: "", fat: "" });
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
      <h1 className="text-2xl font-extrabold">تسجيل الأكل</h1>

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

        <Field label="ابحث في المكتبة أو اكتب اسم الأكلة" value={q} onChange={(e) => setQ(e.target.value)} />
        {results.length > 0 && (
          <div className="border border-gray-100 rounded-xl max-h-52 overflow-auto mb-3">
            {results.map((r) => (
              <button
                key={r.id}
                onClick={() => pickLibrary(r)}
                className="w-full text-right px-4 py-2 hover:bg-gray-50 flex justify-between"
              >
                <span>{r.name_ar}</span>
                <span className="text-muted text-sm">{r.calories_per_100} سعرة/100جم</span>
              </button>
            ))}
          </div>
        )}

        <form onSubmit={add}>
          <Field label="اسم الأكلة" value={form.name_ar} onChange={(e) => set("name_ar", e.target.value)} />
          <div className="grid grid-cols-2 md:grid-cols-3 gap-x-3">
            <Field label="الكمية (جم)" type="number" value={form.amount} onChange={(e) => set("amount", e.target.value)} />
            <Field label="سعرات" type="number" value={form.calories} onChange={(e) => set("calories", e.target.value)} />
            <Field label="بروتين" type="number" value={form.protein} onChange={(e) => set("protein", e.target.value)} />
            <Field label="نشويات" type="number" value={form.carbs} onChange={(e) => set("carbs", e.target.value)} />
            <Field label="دهون" type="number" value={form.fat} onChange={(e) => set("fat", e.target.value)} />
          </div>
          {msg && <p className="text-teal text-sm mb-2">{msg}</p>}
          <div className="flex gap-2">
            <Button variant="outline" onClick={estimate} className="flex-1">قدّر تلقائياً</Button>
            <Button type="submit" className="flex-1">أضف للوجبة</Button>
          </div>
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
                    {MEALS[l.meal]} • {Math.round(l.amount)}جم • {Math.round(l.calories)} سعرة
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
