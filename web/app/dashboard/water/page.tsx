"use client";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { Button, Card, Spinner, StatRow } from "@/components/ui";

export default function WaterPage() {
  const [water, setWater] = useState<any>(null);
  const [drinks, setDrinks] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  async function load() {
    const [w, d] = await Promise.all([api.water(), api.drinks()]);
    setWater(w);
    setDrinks(d);
    setLoading(false);
  }
  useEffect(() => {
    load();
  }, []);

  async function add(ml: number) {
    setWater(await api.addWater(ml));
  }

  if (loading) return <Spinner />;
  const pct = Math.min(water.percent, 100);

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-extrabold">المياه</h1>
      <Card>
        <div className="text-center">
          <div className="text-4xl font-extrabold text-sky">{water.total_ml}</div>
          <div className="text-muted">من {water.goal_ml} مل</div>
          <div className="h-3 rounded-full bg-sky/15 mt-3 overflow-hidden">
            <div className="h-full bg-sky rounded-full transition-all" style={{ width: `${pct}%` }} />
          </div>
          <p className="text-sky mt-3">{water.message_ar}</p>
          <div className="flex gap-2 justify-center mt-4">
            {[150, 250, 500].map((ml) => (
              <Button key={ml} onClick={() => add(ml)} className="bg-sky hover:bg-sky/90">
                +{ml} مل
              </Button>
            ))}
          </div>
        </div>
      </Card>
      <Card>
        <h2 className="font-bold text-lg mb-2">مشروبات تساعدك</h2>
        {drinks.map((d, i) => (
          <StatRow key={i} k={`${d.name_ar} — ${d.note_ar}`} v={`${d.approx_calories} سعرة`} />
        ))}
      </Card>
    </div>
  );
}
