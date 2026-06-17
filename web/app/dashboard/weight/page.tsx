"use client";
import { useEffect, useState } from "react";
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { api } from "@/lib/api";
import { Button, Card, Field, Spinner } from "@/components/ui";

export default function WeightPage() {
  const [trend, setTrend] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [val, setVal] = useState("");

  async function load() {
    setTrend(await api.weightTrend());
    setLoading(false);
  }
  useEffect(() => {
    load();
  }, []);

  async function add(e: React.FormEvent) {
    e.preventDefault();
    const kg = Number(val);
    if (!kg) return;
    await api.addWeight(kg);
    setVal("");
    load();
  }

  if (loading) return <Spinner />;
  const points = (trend?.points || []).map((p: any) => ({
    day: p.day.slice(5),
    "الوزن": p.raw_kg,
    "الاتجاه": p.trend_kg,
  }));
  const plateau = trend?.plateau;

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-extrabold">الوزن</h1>

      <Card>
        <form onSubmit={add} className="flex gap-2 items-end">
          <div className="flex-1">
            <Field label="وزنك النهاردة (كجم)" type="number" step="0.1" value={val} onChange={(e) => setVal(e.target.value)} />
          </div>
          <Button type="submit" className="mb-3">سجّل</Button>
        </form>
        <p className="text-muted text-sm">
          بنتابع وزنك بالاتجاه (المتوسط) مش الرقم اليومي • يوم الوزن المفضّل:{" "}
          {trend?.suggested_weigh_in_day_ar || "الجمعة"} الصبح
        </p>
      </Card>

      <Card>
        <h2 className="font-bold text-lg mb-3">اتجاه الوزن</h2>
        {points.length < 2 ? (
          <p className="text-muted text-center py-6">سجّل وزنك مرتين على الأقل عشان نرسم اتجاهك.</p>
        ) : (
          <div style={{ width: "100%", height: 260 }}>
            <ResponsiveContainer>
              <LineChart data={points} margin={{ top: 10, right: 10, left: -10, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#eee" />
                <XAxis dataKey="day" tick={{ fontSize: 11 }} />
                <YAxis domain={["auto", "auto"]} tick={{ fontSize: 11 }} />
                <Tooltip />
                <Line type="monotone" dataKey="الوزن" stroke="#3C7DD9" strokeWidth={1.5} dot={false} opacity={0.5} />
                <Line type="monotone" dataKey="الاتجاه" stroke="#1B998B" strokeWidth={3} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        )}
      </Card>

      {plateau?.is_plateau && (
        <div className="rounded-xl bg-accent/10 text-accent p-4">📈 {plateau.message_ar}</div>
      )}
    </div>
  );
}
