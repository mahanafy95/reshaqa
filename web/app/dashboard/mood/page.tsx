"use client";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { Button, Card, Spinner } from "@/components/ui";

function Slider({ label, value, min, max, step, onChange, suffix }: any) {
  return (
    <div className="mb-4">
      <div className="flex justify-between mb-1">
        <span className="font-semibold">{label}</span>
        <span className="text-teal font-bold">{value}{suffix}</span>
      </div>
      <input type="range" min={min} max={max} step={step} value={value} onChange={(e) => onChange(Number(e.target.value))} className="w-full accent-teal" />
    </div>
  );
}

export default function MoodPage() {
  const [loading, setLoading] = useState(true);
  const [energy, setEnergy] = useState(3);
  const [sleep, setSleep] = useState(7);
  const [hunger, setHunger] = useState(3);
  const [msg, setMsg] = useState<string | null>(null);

  useEffect(() => {
    (async () => {
      const m = await api.mood();
      if (m) {
        setEnergy(m.energy ?? 3);
        setSleep(m.sleep_hours ?? 7);
        setHunger(m.hunger ?? 3);
      }
      setLoading(false);
    })();
  }, []);

  async function save() {
    await api.saveMood({ energy, sleep_hours: sleep, hunger });
    setMsg("اتسجّل، شكراً إنك بتتابع حالتك 💚");
  }

  if (loading) return <Spinner />;
  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-extrabold">حاسس بإيه النهاردة؟</h1>
      <Card>
        <Slider label="طاقتك" value={energy} min={1} max={5} step={1} onChange={setEnergy} suffix="/5" />
        <Slider label="ساعات نومك" value={sleep} min={0} max={12} step={0.5} onChange={setSleep} suffix=" ساعة" />
        <Slider label="إحساسك بالجوع" value={hunger} min={1} max={5} step={1} onChange={setHunger} suffix="/5" />
        {msg && <p className="text-teal text-center mb-2">{msg}</p>}
        <Button onClick={save} className="w-full">احفظ</Button>
      </Card>
    </div>
  );
}
