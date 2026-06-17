"use client";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { Button, Card, Field, Spinner } from "@/components/ui";

const today = () => new Date().toISOString().split("T")[0];

export default function ActivityPage() {
  const [list, setList] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [f, setF] = useState({ type_ar: "", duration_min: "", calories_burned: "" });

  async function load() {
    setList(await api.activities(today()));
    setLoading(false);
  }
  useEffect(() => {
    load();
  }, []);

  async function add(e: React.FormEvent) {
    e.preventDefault();
    if (!f.type_ar.trim()) return;
    await api.addActivity({
      date: today(),
      type_ar: f.type_ar.trim(),
      duration_min: Number(f.duration_min) || 0,
      calories_burned: f.calories_burned ? Number(f.calories_burned) : null,
      source: "manual",
    });
    setF({ type_ar: "", duration_min: "", calories_burned: "" });
    load();
  }

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-extrabold">النشاط</h1>
      <div className="rounded-xl bg-accent/10 text-accent p-3 text-sm">
        النشاط بيتسجّل لوحده وما بيتخصمش من ميزانية أكلك.
      </div>
      <Card>
        <form onSubmit={add}>
          <div className="flex gap-2 flex-wrap mb-2">
            {["مشي", "جري", "جيم", "سباحة", "دراجة"].map((t) => (
              <button key={t} type="button" onClick={() => setF({ ...f, type_ar: t })} className="rounded-full bg-gray-100 px-3 py-1 text-sm">
                {t}
              </button>
            ))}
          </div>
          <Field label="نوع النشاط" value={f.type_ar} onChange={(e) => setF({ ...f, type_ar: e.target.value })} />
          <div className="grid grid-cols-2 gap-x-3">
            <Field label="المدة (دقيقة)" type="number" value={f.duration_min} onChange={(e) => setF({ ...f, duration_min: e.target.value })} />
            <Field label="سعرات محروقة (اختياري)" type="number" value={f.calories_burned} onChange={(e) => setF({ ...f, calories_burned: e.target.value })} />
          </div>
          <Button type="submit" className="w-full">سجّل النشاط</Button>
        </form>
      </Card>
      <Card>
        <h2 className="font-bold text-lg mb-2">نشاط النهاردة</h2>
        {loading ? (
          <Spinner />
        ) : list.length === 0 ? (
          <p className="text-muted text-center py-3">مفيش نشاط متسجّل.</p>
        ) : (
          list.map((a) => (
            <div key={a.id} className="flex justify-between items-center py-2 border-b border-gray-50 last:border-0">
              <div>
                <div className="font-semibold">{a.type_ar}</div>
                <div className="text-muted text-sm">
                  {[a.duration_min ? `${a.duration_min} دقيقة` : null, a.calories_burned ? `${Math.round(a.calories_burned)} سعرة` : null].filter(Boolean).join(" • ")}
                </div>
              </div>
              <button onClick={async () => { await api.deleteActivity(a.id); load(); }} className="text-red-500 text-sm">حذف</button>
            </div>
          ))
        )}
      </Card>
    </div>
  );
}
