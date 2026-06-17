"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api, ApiError } from "@/lib/api";
import { Bar, Card, Spinner, StatRow } from "@/components/ui";

const MACRO_COLORS: Record<string, string> = { بروتين: "#1B998B", نشويات: "#E08A3C", دهون: "#3C7DD9" };

export default function DashboardHome() {
  const router = useRouter();
  const [summary, setSummary] = useState<any>(null);
  const [targets, setTargets] = useState<any>(null);
  const [water, setWater] = useState<any>(null);
  const [body, setBody] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    (async () => {
      try {
        const profile = await api.getProfile();
        if (!profile) {
          router.replace("/dashboard/profile");
          return;
        }
        const [s, t, w, b] = await Promise.all([api.summary(), api.targets(), api.water(), api.bodyMetrics()]);
        setSummary(s);
        setTargets(t);
        setWater(w);
        setBody(b);
      } catch (e) {
        if (e instanceof ApiError && e.status === 401) router.replace("/login");
      } finally {
        setLoading(false);
      }
    })();
  }, [router]);

  if (loading) return <Spinner />;
  if (!summary) return <p className="text-muted">تعذّر تحميل البيانات.</p>;

  const remaining = summary.remaining_calories;
  const plateau = targets?.plateau;

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-extrabold">ملخص النهاردة</h1>

      <Card>
        <div className="flex items-center gap-6 flex-wrap">
          <div>
            <div className="text-4xl font-extrabold text-teal">{Math.round(summary.eaten_calories)}</div>
            <div className="text-muted text-sm">من {Math.round(summary.target_calories)} سعرة</div>
          </div>
          <div className="flex-1 min-w-[160px]">
            <div className="h-3 rounded-full bg-gray-100 overflow-hidden">
              <div
                className="h-full rounded-full"
                style={{
                  width: `${Math.min(summary.percent_of_target, 100)}%`,
                  background: remaining < 0 ? "#E08A3C" : "#1B998B",
                }}
              />
            </div>
            <div className={`mt-2 font-bold ${remaining < 0 ? "text-accent" : "text-teal"}`}>
              {remaining >= 0 ? `باقي ${Math.round(remaining)} سعرة` : `زيادة ${Math.round(-remaining)} سعرة`}
            </div>
          </div>
          <span className="rounded-full bg-teal/10 text-teal px-3 py-1 text-sm font-semibold">
            وضع {summary.mode === "maintain" ? "تثبيت" : "تخسيس"}
          </span>
        </div>
        <div className="mt-4 rounded-xl bg-teal/5 text-teal-dark p-3 text-center">{summary.encouragement_ar}</div>
      </Card>

      <Card>
        <h2 className="font-bold text-lg mb-2">الماكروز</h2>
        {summary.macros.map((m: any) => (
          <Bar key={m.name_ar} label={m.name_ar} eaten={m.eaten} target={m.target} color={MACRO_COLORS[m.name_ar] || "#1B998B"} />
        ))}
        <p className="text-muted text-sm mt-2 text-center">{summary.calories_status.message_ar}</p>
      </Card>

      {plateau?.is_plateau && (
        <div className="rounded-xl bg-accent/10 text-accent p-4 flex gap-2">
          <span>📈</span>
          <span>{plateau.message_ar}</span>
        </div>
      )}

      {water && (
        <Card>
          <div className="flex items-center gap-3">
            <span className="text-2xl">💧</span>
            <div className="flex-1">
              <div className="font-semibold">
                المياه: {water.total_ml} / {water.goal_ml} مل
              </div>
              <div className="h-2 rounded-full bg-sky/15 mt-1 overflow-hidden">
                <div className="h-full bg-sky rounded-full" style={{ width: `${Math.min(water.percent, 100)}%` }} />
              </div>
            </div>
          </div>
        </Card>
      )}

      {body && (
        <Card>
          <h2 className="font-bold text-lg mb-2">مؤشرات الجسم</h2>
          <StatRow k="مؤشر الكتلة (BMI)" v={`${body.bmi} — ${body.bmi_category_ar}`} />
          <StatRow k="النطاق الصحي لوزنك" v={`${body.healthy_min_kg} - ${body.healthy_max_kg} كجم`} />
          {body.body_fat_pct != null && <StatRow k="نسبة الدهون (تقديرية)" v={`${body.body_fat_pct}%`} />}
          {body.lean_mass_kg != null && <StatRow k="الكتلة الصافية / الدهون" v={`${body.lean_mass_kg} / ${body.fat_mass_kg} كجم`} />}
          <p className="text-muted text-xs mt-2">{body.note_ar}</p>
        </Card>
      )}

      <p className="text-muted text-sm text-center">النشاط بيتسجّل لوحده وما بيتخصمش من ميزانية الأكل.</p>
    </div>
  );
}
