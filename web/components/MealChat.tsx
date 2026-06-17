"use client";
import { useEffect, useRef, useState } from "react";
import { api, ApiError } from "@/lib/api";
import { Button } from "@/components/ui";

const MEALS: Record<string, string> = { breakfast: "فطار", lunch: "غدا", dinner: "عشا", snack: "سناك" };
const today = () => new Date().toISOString().split("T")[0];

type Item = {
  name_ar: string; qty: number; unit: string | null; grams: number; meal: string;
  calories: number; protein: number; carbs: number; fat: number; confidence: string; note_ar: string;
};
type Msg = { role: "user" | "bot"; text: string };

const CONF: Record<string, string> = { high: "bg-teal/10 text-teal", medium: "bg-amber-100 text-amber-700", low: "bg-gray-100 text-gray-500" };

export default function MealChat({
  defaultMeal,
  todayTotal,
  onLogged,
}: {
  defaultMeal: string;
  todayTotal: number;
  onLogged: () => void;
}) {
  const [msgs, setMsgs] = useState<Msg[]>([
    { role: "bot", text: "اكتبلي أكلت إيه بالعامية، مثلاً: «النهاردة فطرت بيضتين وكوباية لبن ورغيف، وعلى الغدا طبق رز وفرخة». أنا أفهمه وأحسب السعرات وأسجّلهولك." },
  ]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [pending, setPending] = useState<Item[]>([]);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [msgs, pending]);

  async function send() {
    const text = input.trim();
    if (!text || busy) return;
    setMsgs((m) => [...m, { role: "user", text }]);
    setInput("");
    setBusy(true);
    try {
      const r = await api.parseMeal(text, { date: today(), default_meal: defaultMeal, confirm: false });
      setMsgs((m) => [...m, { role: "bot", text: r.reply_ar || "فهمت." }]);
      setPending(r.items || []);
    } catch (e) {
      setMsgs((m) => [...m, { role: "bot", text: e instanceof ApiError ? e.message : "حصل خطأ، حاول تاني." }]);
    } finally {
      setBusy(false);
    }
  }

  function patch(i: number, p: Partial<Item>) {
    setPending((prev) => prev.map((it, idx) => (idx === i ? { ...it, ...p } : it)));
  }

  const pendingTotal = pending.reduce((s, x) => s + (Number(x.calories) || 0), 0);

  async function logAll() {
    if (!pending.length || busy) return;
    setBusy(true);
    try {
      for (const it of pending) {
        await api.addFood({
          date: today(),
          meal: it.meal,
          name_ar: it.name_ar,
          amount: it.grams || 1,
          calories: Number(it.calories) || 0,
          protein: Number(it.protein) || 0,
          carbs: Number(it.carbs) || 0,
          fat: Number(it.fat) || 0,
          source: "manual",
        });
      }
      setMsgs((m) => [
        ...m,
        { role: "bot", text: `تمام ✅ سجّلت ${pending.length} صنف بمجموع ${Math.round(pendingTotal)} سعرة. مجموع يومك بقى ≈ ${Math.round(todayTotal + pendingTotal)} سعرة.` },
      ]);
      setPending([]);
      onLogged();
    } catch (e) {
      setMsgs((m) => [...m, { role: "bot", text: e instanceof ApiError ? e.message : "فشل التسجيل." }]);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="bg-white rounded-2xl shadow-sm p-4">
      <div className="flex items-center gap-2 mb-2">
        <span className="text-xl">🤖</span>
        <h2 className="font-bold text-lg">مساعد الأكل — كلّمني بالعامية</h2>
      </div>

      <div ref={scrollRef} className="max-h-72 overflow-auto space-y-2 mb-3 p-1">
        {msgs.map((m, i) => (
          <div key={i} className={`flex ${m.role === "user" ? "justify-start" : "justify-end"}`}>
            <div
              className={`max-w-[85%] rounded-2xl px-3 py-2 text-sm whitespace-pre-line ${
                m.role === "user" ? "bg-teal text-white" : "bg-gray-100 text-ink"
              }`}
            >
              {m.text}
            </div>
          </div>
        ))}
      </div>

      {pending.length > 0 && (
        <div className="rounded-xl border border-gray-100 p-2 mb-3 space-y-1">
          <div className="text-xs text-muted mb-1">راجع/عدّل قبل التسجيل:</div>
          {pending.map((it, i) => (
            <div key={i} className="flex items-center gap-2 text-sm border-b border-gray-50 last:border-0 py-1">
              <span className={`text-[10px] rounded px-1.5 py-0.5 ${CONF[it.confidence] || CONF.medium}`}>
                {it.confidence === "high" ? "مؤكد" : it.confidence === "low" ? "تقديري" : "تقريبي"}
              </span>
              <span className="flex-1 font-semibold">{it.name_ar}</span>
              <select
                value={it.meal}
                onChange={(e) => patch(i, { meal: e.target.value })}
                className="text-xs rounded-lg border border-gray-200 px-1.5 py-1"
              >
                {Object.entries(MEALS).map(([k, v]) => (
                  <option key={k} value={k}>{v}</option>
                ))}
              </select>
              <input
                type="number"
                value={it.calories}
                onChange={(e) => patch(i, { calories: Number(e.target.value) })}
                className="w-16 text-xs rounded-lg border border-gray-200 px-1.5 py-1 text-center"
              />
              <span className="text-muted text-xs">سعرة</span>
              <button onClick={() => setPending((p) => p.filter((_, idx) => idx !== i))} className="text-red-500 text-xs">✕</button>
            </div>
          ))}
          <div className="flex items-center justify-between pt-1">
            <span className="text-sm font-bold text-teal">المجموع ≈ {Math.round(pendingTotal)} سعرة</span>
            <Button onClick={logAll} disabled={busy} className="text-sm py-1.5">سجّل الكل</Button>
          </div>
        </div>
      )}

      <div className="flex gap-2">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && send()}
          placeholder="اكتب أكلت إيه…"
          className="flex-1 rounded-xl border border-gray-200 bg-white px-4 py-2.5 outline-none focus:border-teal"
        />
        <Button onClick={send} disabled={busy}>{busy ? "…" : "ابعت"}</Button>
      </div>
    </div>
  );
}
