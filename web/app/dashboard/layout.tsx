"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { clearToken, isAuthed } from "@/lib/auth";
import { api } from "@/lib/api";

const NAV = [
  { href: "/dashboard", label: "الرئيسية", icon: "🏠" },
  { href: "/dashboard/foods", label: "تسجيل الأكل", icon: "🍽️" },
  { href: "/dashboard/assistant", label: "المساعد الذكي", icon: "🤖" },
  { href: "/dashboard/recipes", label: "الوصفات", icon: "📖" },
  { href: "/dashboard/weight", label: "الوزن", icon: "⚖️" },
  { href: "/dashboard/water", label: "المياه", icon: "💧" },
  { href: "/dashboard/activity", label: "النشاط", icon: "🏃" },
  { href: "/dashboard/mood", label: "حاسس بإيه", icon: "😊" },
  { href: "/dashboard/reports", label: "التقارير", icon: "📊" },
  { href: "/dashboard/profile", label: "بياناتي", icon: "👤" },
];

const ADMIN_NAV = { href: "/dashboard/admin", label: "الإشراف", icon: "🛡️" };

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const [ready, setReady] = useState(false);
  const [isAdmin, setIsAdmin] = useState(false);
  const [dark, setDark] = useState(false);

  useEffect(() => {
    if (!isAuthed()) {
      router.replace("/login");
      return;
    }
    setReady(true);
    setDark(document.documentElement.classList.contains("dark"));
    api.me().then((u) => setIsAdmin(!!u?.is_admin)).catch(() => {});
  }, [router]);

  function toggleTheme() {
    const el = document.documentElement;
    const next = !el.classList.contains("dark");
    el.classList.toggle("dark", next);
    try {
      localStorage.setItem("theme", next ? "dark" : "light");
    } catch {
      /* ignore */
    }
    setDark(next);
  }

  const nav = isAdmin ? [...NAV, ADMIN_NAV] : NAV;

  if (!ready) return <div className="min-h-screen grid place-items-center text-muted">جارٍ التحميل…</div>;

  function logout() {
    clearToken();
    router.replace("/login");
  }

  return (
    <div className="min-h-screen flex">
      <aside className="w-60 bg-surface border-l border-line flex flex-col shrink-0 max-md:hidden">
        <div className="p-5 text-center border-b border-line">
          <div className="text-2xl">🥗</div>
          <div className="font-extrabold text-teal text-xl">رشاقة</div>
        </div>
        <nav className="flex-1 p-3 space-y-1">
          {nav.map((n) => {
            const active = pathname === n.href;
            return (
              <Link
                key={n.href}
                href={n.href}
                className={`flex items-center gap-3 rounded-xl px-4 py-2.5 transition ${
                  active ? "bg-teal text-white" : "hover:bg-soft text-ink"
                }`}
              >
                <span>{n.icon}</span>
                <span className="font-semibold">{n.label}</span>
              </Link>
            );
          })}
        </nav>
        <button onClick={toggleTheme} className="mx-3 rounded-xl px-4 py-2.5 hover:bg-soft text-ink text-right flex items-center gap-3">
          <span>{dark ? "☀️" : "🌙"}</span>
          <span className="font-semibold">{dark ? "الوضع الفاتح" : "الوضع الليلي"}</span>
        </button>
        <button onClick={logout} className="m-3 rounded-xl px-4 py-2.5 text-red-600 hover:bg-red-50 text-right">
          🚪 تسجيل الخروج
        </button>
      </aside>

      {/* شريط علوي للموبايل */}
      <div className="flex-1 flex flex-col min-w-0">
        <header className="md:hidden bg-teal text-white px-4 py-3 flex items-center justify-between">
          <span className="font-extrabold text-lg">🥗 رشاقة</span>
          <div className="flex items-center gap-3">
            <button onClick={toggleTheme} aria-label="تبديل الوضع" className="text-lg">{dark ? "☀️" : "🌙"}</button>
            <button onClick={logout} className="text-sm">خروج</button>
          </div>
        </header>
        <nav className="md:hidden flex overflow-x-auto bg-surface border-b border-line px-2 py-2 gap-1">
          {nav.map((n) => {
            const active = pathname === n.href;
            return (
              <Link
                key={n.href}
                href={n.href}
                className={`whitespace-nowrap rounded-lg px-3 py-1.5 text-sm ${
                  active ? "bg-teal text-white" : "text-muted"
                }`}
              >
                {n.label}
              </Link>
            );
          })}
        </nav>
        <main className="flex-1 p-4 md:p-6 max-w-4xl w-full mx-auto">{children}</main>
      </div>
    </div>
  );
}
