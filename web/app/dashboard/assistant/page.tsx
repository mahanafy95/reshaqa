"use client";
import { useEffect, useRef, useState } from "react";
import { api, ApiError } from "@/lib/api";
import { Button } from "@/components/ui";

type Msg = { role: "user" | "assistant"; content: string };

const PROMPTS = [
  "اعملي خطة أكل بسيطة لإنقاص الوزن",
  "إيه أحسن أكلات غنية بالبروتين ورخيصة؟",
  "حابب أحافظ على نشاطي، اقترح روتين رياضي للمبتدئين",
  "حسّسني بالحماس، نفسي أكمل على الدايت",
  "وصفة عشاء صحية وسريعة",
];

const FALLBACK = "المساعد الذكي مش متفعّل دلوقتي. جرّب تاني بعد شوية 🙏";

export default function AssistantPage() {
  const [msgs, setMsgs] = useState<Msg[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [msgs, busy]);

  async function send(text?: string) {
    const content = (text ?? input).trim();
    if (!content || busy) return;
    const next: Msg[] = [...msgs, { role: "user", content }];
    setMsgs(next);
    setInput("");
    setBusy(true);
    try {
      // نبعت آخر ~8 رسائل فقط للحفاظ على السياق دون إثقال الطلب
      const recent = next.slice(-8);
      const r = await api.assistantChat(recent);
      setMsgs((m) => [...m, { role: "assistant", content: r?.reply || FALLBACK }]);
    } catch (e) {
      setMsgs((m) => [
        ...m,
        { role: "assistant", content: e instanceof ApiError ? e.message : FALLBACK },
      ]);
    } finally {
      setBusy(false);
    }
  }

  const empty = msgs.length === 0;

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-extrabold">المساعد الذكي 🤖</h1>

      <div className="bg-white rounded-2xl shadow-sm p-4 flex flex-col" style={{ minHeight: "60vh" }}>
        <div ref={scrollRef} className="flex-1 overflow-auto space-y-3 p-1">
          {empty ? (
            <div className="h-full flex flex-col items-center justify-center text-center gap-4 py-8">
              <div className="text-4xl">🤖</div>
              <p className="text-muted max-w-sm">
                اسألني أي حاجة عن الأكل الصحي، الرياضة، الوصفات، أهدافك، أو حتى محتاج تحفيز.
                أنا هنا أساعدك.
              </p>
              <div className="flex flex-wrap gap-2 justify-center">
                {PROMPTS.map((p) => (
                  <button
                    key={p}
                    onClick={() => send(p)}
                    disabled={busy}
                    className="rounded-full border border-teal/40 text-teal text-sm px-3 py-1.5 hover:bg-teal/5 transition disabled:opacity-50"
                  >
                    {p}
                  </button>
                ))}
              </div>
            </div>
          ) : (
            msgs.map((m, i) => (
              <div key={i} className={`flex ${m.role === "user" ? "justify-start" : "justify-end"}`}>
                <div
                  className={`max-w-[85%] rounded-2xl px-4 py-2.5 text-sm whitespace-pre-line leading-relaxed ${
                    m.role === "user" ? "bg-teal text-white" : "bg-gray-100 text-ink"
                  }`}
                >
                  {m.content}
                </div>
              </div>
            ))
          )}
          {busy && (
            <div className="flex justify-end">
              <div className="bg-gray-100 text-muted rounded-2xl px-4 py-2.5 text-sm">…بكتب</div>
            </div>
          )}
        </div>

        <div className="flex gap-2 pt-3">
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") send();
            }}
            placeholder="اكتب رسالتك…"
            disabled={busy}
            className="flex-1 rounded-xl border border-gray-200 bg-white px-4 py-2.5 outline-none focus:border-teal disabled:opacity-60"
          />
          <Button onClick={() => send()} disabled={busy}>
            {busy ? "…" : "ابعت"}
          </Button>
        </div>
      </div>
    </div>
  );
}
