"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api, ApiError } from "@/lib/api";
import { Button, Card, Field, Select, Spinner, StatRow } from "@/components/ui";

const ACTIVITY: Record<string, string> = {
  sedentary: "خامل (قليل الحركة)",
  light: "نشاط خفيف",
  moderate: "نشاط متوسط",
  active: "نشاط عالٍ",
};

export default function ProfilePage() {
  const router = useRouter();
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [existing, setExisting] = useState<any>(null);
  const [f, setF] = useState({
    age: "30", sex: "female", height_cm: "165", weight_kg: "80",
    activity_level: "light", goal_weight_kg: "", goal_rate: "0.5",
  });

  useEffect(() => {
    (async () => {
      try {
        const p = await api.getProfile();
        if (p) {
          setExisting(p);
          setF({
            age: String(p.age), sex: p.sex, height_cm: String(p.height_cm), weight_kg: String(p.weight_kg),
            activity_level: p.activity_level, goal_weight_kg: p.goal_weight_kg ? String(p.goal_weight_kg) : "",
            goal_rate: p.goal_rate ? String(p.goal_rate) : "0.5",
          });
        }
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  async function save(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const p = await api.saveProfile({
        age: Number(f.age), sex: f.sex, height_cm: Number(f.height_cm), weight_kg: Number(f.weight_kg),
        activity_level: f.activity_level,
        goal_weight_kg: f.goal_weight_kg ? Number(f.goal_weight_kg) : null,
        goal_rate: Number(f.goal_rate),
      });
      setExisting(p);
      router.push("/dashboard");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "حصل خطأ.");
    } finally {
      setBusy(false);
    }
  }

  if (loading) return <Spinner />;
  const set = (k: string, v: string) => setF({ ...f, [k]: v });

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-extrabold">بياناتي</h1>
      {existing && (
        <Card>
          <StatRow k="النطاق الصحي لوزنك" v={`${existing.healthy_min_kg} - ${existing.healthy_max_kg} كجم`} />
        </Card>
      )}
      <Card>
        <form onSubmit={save}>
          <div className="grid md:grid-cols-2 gap-x-4">
            <Field label="العمر" type="number" value={f.age} onChange={(e) => set("age", e.target.value)} />
            <Select label="الجنس" value={f.sex} onChange={(e) => set("sex", e.target.value)}>
              <option value="female">أنثى</option>
              <option value="male">ذكر</option>
            </Select>
            <Field label="الطول (سم)" type="number" value={f.height_cm} onChange={(e) => set("height_cm", e.target.value)} />
            <Field label="الوزن الحالي (كجم)" type="number" value={f.weight_kg} onChange={(e) => set("weight_kg", e.target.value)} />
            <Select label="مستوى النشاط" value={f.activity_level} onChange={(e) => set("activity_level", e.target.value)}>
              {Object.entries(ACTIVITY).map(([k, v]) => (
                <option key={k} value={k}>{v}</option>
              ))}
            </Select>
            <Field label="الوزن المستهدف (اختياري)" type="number" value={f.goal_weight_kg} onChange={(e) => set("goal_weight_kg", e.target.value)} />
            <Select label="معدل النزول (كجم/أسبوع)" value={f.goal_rate} onChange={(e) => set("goal_rate", e.target.value)}>
              <option value="0.25">0.25 (بطيء ومريح)</option>
              <option value="0.5">0.5 (معتدل)</option>
              <option value="0.75">0.75 (أسرع)</option>
            </Select>
          </div>
          {error && <p className="text-red-600 text-sm my-2">{error}</p>}
          <Button type="submit" disabled={busy} className="w-full mt-2">
            {busy ? "..." : "احسبلي هدفي"}
          </Button>
        </form>
      </Card>
    </div>
  );
}
