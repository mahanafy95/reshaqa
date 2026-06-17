"use client";
import { useEffect, useState } from "react";
import { Bar, BarChart, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { api, downloadBlob } from "@/lib/api";
import { Button, Card, Spinner, StatRow } from "@/components/ui";

const STATUS_COLOR: Record<string, string> = {
  "ضمن الهدف": "#1B998B",
  "فوق الهدف": "#E08A3C",
  "تحت الهدف": "#3C7DD9",
  "لا يوجد تسجيل": "#D1D5DB",
};

export default function ReportsPage() {
  const [tab, setTab] = useState<"weekly" | "monthly">("weekly");
  const [weekly, setWeekly] = useState<any>(null);
  const [monthly, setMonthly] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    (async () => {
      const now = new Date();
      const [w, m] = await Promise.all([api.weekly(), api.monthly(now.getFullYear(), now.getMonth() + 1)]);
      setWeekly(w);
      setMonthly(m);
      setLoading(false);
    })();
  }, []);

  async function downloadWeekly() {
    const blob = await api.weeklyPdf();
    downloadBlob(blob, "تقرير_اسبوعي.pdf");
  }
  async function downloadMonthly() {
    const now = new Date();
    const blob = await api.monthlyPdf(now.getFullYear(), now.getMonth() + 1);
    downloadBlob(blob, "تقرير_شهري.pdf");
  }

  if (loading) return <Spinner />;

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-extrabold">التقارير</h1>
      <div className="flex gap-2">
        {(["weekly", "monthly"] as const).map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`rounded-full px-5 py-2 font-semibold ${tab === t ? "bg-teal text-white" : "bg-white text-muted"}`}
          >
            {t === "weekly" ? "أسبوعي" : "شهري"}
          </button>
        ))}
      </div>

      {tab === "weekly" && weekly && (
        <>
          <Card>
            <h2 className="font-bold mb-2">
              أسبوع {weekly.start} → {weekly.end}
            </h2>
            <StatRow k="أيام الالتزام" v={`${weekly.adherent_days} من 7`} />
            <StatRow k="توزيع الأيام" v={`ضمن ${weekly.days_within} • فوق ${weekly.days_over} • تحت ${weekly.days_under}`} />
            <StatRow k="متوسط المتناول" v={`${weekly.avg_eaten} سعرة (هدف ${weekly.avg_target})`} />
            <StatRow k="متوسط الماكروز" v={`ب ${weekly.avg_protein} • ن ${weekly.avg_carbs} • د ${weekly.avg_fat}`} />
            {weekly.water_avg_ml > 0 && <StatRow k="متوسط المياه" v={`${weekly.water_avg_ml} مل/يوم`} />}
            {weekly.activity_total_min > 0 && <StatRow k="النشاط" v={`${weekly.activity_total_min} دقيقة • ${weekly.activity_total_calories} سعرة`} />}
            {weekly.weight_change_kg != null && <StatRow k="تغيّر الوزن" v={`${weekly.weight_change_kg} كجم`} />}
          </Card>

          <Card>
            <h2 className="font-bold mb-3">التزام الأيام</h2>
            <div style={{ width: "100%", height: 200 }}>
              <ResponsiveContainer>
                <BarChart data={weekly.days.map((d: any) => ({ day: d.day.slice(5), سعرات: d.eaten_calories, status: d.status }))}>
                  <XAxis dataKey="day" tick={{ fontSize: 11 }} />
                  <YAxis tick={{ fontSize: 11 }} />
                  <Tooltip />
                  <Bar dataKey="سعرات" radius={[6, 6, 0, 0]}>
                    {weekly.days.map((d: any, i: number) => (
                      <Cell key={i} fill={STATUS_COLOR[d.status] || "#ccc"} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          </Card>

          <div className="rounded-xl bg-teal/5 text-teal-dark p-3 text-center">{weekly.summary_ar}</div>
          <Button onClick={downloadWeekly} className="w-full">⬇️ تنزيل PDF (للطبيب)</Button>
        </>
      )}

      {tab === "monthly" && monthly && (
        <>
          <Card>
            <h2 className="font-bold mb-2">ملخص الشهر</h2>
            <StatRow k="إجمالي أيام الالتزام" v={`${monthly.total_adherent_days} يوم`} />
            <StatRow k="أيام التسجيل" v={`${monthly.total_logged_days} يوم`} />
            <StatRow k="متوسط المتناول" v={`${monthly.avg_eaten} سعرة`} />
            <StatRow k="متوسط الماكروز" v={`ب ${monthly.avg_protein} • ن ${monthly.avg_carbs} • د ${monthly.avg_fat}`} />
            {monthly.water_avg_ml > 0 && <StatRow k="متوسط المياه" v={`${monthly.water_avg_ml} مل/يوم`} />}
            {monthly.weight_change_kg != null && <StatRow k="تغيّر الوزن" v={`${monthly.weight_change_kg} كجم`} />}
          </Card>
          <Card>
            <h2 className="font-bold mb-2">مقارنة الأسابيع</h2>
            {monthly.weeks.map((w: any, i: number) => (
              <StatRow key={i} k={`الأسبوع ${i + 1}`} v={`التزام ${w.adherent_days}/7 • ${w.avg_eaten} سعرة`} />
            ))}
          </Card>
          <div className="rounded-xl bg-teal/5 text-teal-dark p-3 text-center">{monthly.summary_ar}</div>
          <Button onClick={downloadMonthly} className="w-full">⬇️ تنزيل PDF (للطبيب)</Button>
        </>
      )}
    </div>
  );
}
