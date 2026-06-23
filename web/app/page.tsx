"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { isAuthed } from "@/lib/auth";

const FEATURES = [
  { icon: "🍽️", title: "سجّل أكلك بأي طريقة", body: "اكتبه بالكلام، اختاره من المكتبة، امسح الباركود، أو صوّر الملصق." },
  { icon: "🤖", title: "مساعد ذكي بالعربي", body: "اسأله عن أي أكل أو نصيحة، وقوله «ضيف اللي أكلته» فيسجّله في يومك." },
  { icon: "🔥", title: "سلسلة وتحفيز", body: "حافظ على سلسلة أيامك واكسب الشارات — التزام أسهل ومتعة أكتر." },
  { icon: "📈", title: "توقّع وصولك لهدفك", body: "«بمعدّلك الحالي توصل لوزنك خلال كذا أسبوع» — متابعة بالاتجاه مش الرقم اليومي." },
  { icon: "🥗", title: "يناسب نظامك", body: "حلال، نباتي، كيتو، وحساسية — والمساعد يحترمها في اقتراحاته." },
  { icon: "📊", title: "تقارير وتتبّع شامل", body: "وزن، مياه، نشاط، ومزاج — وتقارير أسبوعية ومحيط الخصر." },
];

export default function Home() {
  const router = useRouter();
  const [ready, setReady] = useState(false);

  useEffect(() => {
    if (isAuthed()) router.replace("/dashboard");
    else setReady(true);
  }, [router]);

  if (!ready) return <div className="min-h-screen grid place-items-center text-muted">جارٍ التحميل…</div>;

  return (
    <main className="min-h-screen bg-sand text-ink">
      <header className="max-w-5xl mx-auto px-5 py-5 flex items-center justify-between">
        <div className="flex items-center gap-2 font-extrabold text-xl text-teal">
          <span>🥗</span> رشاقة
        </div>
        <Link href="/login" className="text-teal font-semibold hover:underline">دخول</Link>
      </header>

      <section className="max-w-5xl mx-auto px-5 pt-8 pb-14 text-center">
        <h1 className="text-3xl sm:text-4xl font-extrabold leading-snug">
          رفيقك الصحي لحساب السعرات<br />والوصول لوزنك المثالي
        </h1>
        <p className="text-muted mt-4 max-w-xl mx-auto leading-relaxed">
          تطبيق عربي بسيط: سجّل أكلك بسهولة، تابع وزنك، واستعن بمساعد ذكي يفهمك — مجاناً.
        </p>
        <div className="mt-8 flex flex-wrap gap-3 justify-center">
          <a href="https://reshaqa-app.web.app/reshaqa-latest" rel="noopener"
            className="bg-teal text-white font-bold rounded-xl px-6 py-3 hover:bg-teal-dark transition">
            ⬇️ نزّل تطبيق أندرويد
          </a>
          <Link href="/login"
            className="border border-teal text-teal font-bold rounded-xl px-6 py-3 hover:bg-teal/5 transition">
            افتح لوحة الويب
          </Link>
        </div>
        <p className="text-muted text-xs mt-3">نسخة أندرويد (APK) — فعّل «تثبيت من مصادر غير معروفة» عند الطلب.</p>
      </section>

      <section className="max-w-5xl mx-auto px-5 pb-16">
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {FEATURES.map((f) => (
            <div key={f.title} className="bg-surface rounded-2xl p-5 shadow-sm border border-black/5">
              <div className="text-3xl">{f.icon}</div>
              <h3 className="font-bold mt-3">{f.title}</h3>
              <p className="text-muted text-sm mt-1 leading-relaxed">{f.body}</p>
            </div>
          ))}
        </div>
      </section>

      <footer className="border-t border-black/5">
        <div className="max-w-5xl mx-auto px-5 py-6 text-center text-muted text-sm">
          <div className="flex gap-4 justify-center mb-2">
            <Link href="/privacy" className="hover:underline">سياسة الخصوصية</Link>
            <Link href="/login" className="hover:underline">دخول</Link>
          </div>
          <p>رشاقة — أداة توعية لتتبّع التغذية، وليست بديلاً عن استشارة طبية.</p>
        </div>
      </footer>
    </main>
  );
}
