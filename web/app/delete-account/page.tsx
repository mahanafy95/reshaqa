"use client";
import { useState } from "react";
import { api, ApiError } from "@/lib/api";
import { getToken, clearToken } from "@/lib/auth";

const CONTACT = "mahmoud.ha.hanafy@gmail.com";

export default function DeleteAccountPage() {
  const [busy, setBusy] = useState(false);
  const [done, setDone] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [confirm, setConfirm] = useState(false);
  const loggedIn = typeof window !== "undefined" && !!getToken();

  async function doDelete() {
    setBusy(true);
    setError(null);
    try {
      await api.deleteAccount();
      clearToken();
      setDone(true);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "حصل خطأ. حاول تاني.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div dir="rtl" className="min-h-screen bg-gray-50 py-10 px-4">
      <div className="max-w-md mx-auto bg-white rounded-2xl shadow-sm p-6 md:p-8">
        <h1 className="text-2xl font-extrabold text-teal mb-3">حذف الحساب 🗑️</h1>

        {done ? (
          <p className="text-teal font-semibold">
            تم حذف حسابك وكل بياناتك نهائياً. شكراً إنك جرّبت رشاقة 💚
          </p>
        ) : (
          <>
            <p className="text-gray-700 leading-relaxed mb-4">
              حذف الحساب بيمسح <span className="font-semibold">كل بياناتك نهائياً</span>: ملفك
              الشخصي، سجلّات الأكل والوزن والمياه، والوصفات. الإجراء ده لا يمكن التراجع عنه.
            </p>

            <div className="rounded-xl bg-gray-50 p-4 text-sm text-gray-600 mb-5">
              <p className="font-semibold mb-1">طرق الحذف:</p>
              <ul className="list-disc pr-5 space-y-1">
                <li>من تطبيق الأندرويد: الإعدادات ← حذف حسابي.</li>
                <li>من هنا مباشرةً (لو مسجّل دخول على الويب) بالزر تحت.</li>
                <li>
                  أو راسلنا على{" "}
                  <a href={`mailto:${CONTACT}`} className="text-teal underline">{CONTACT}</a>.
                </li>
              </ul>
            </div>

            {loggedIn ? (
              <>
                <label className="flex items-center gap-2 mb-4 text-sm">
                  <input type="checkbox" checked={confirm} onChange={(e) => setConfirm(e.target.checked)} />
                  أنا متأكد إني عايز أحذف حسابي وكل بياناتي نهائياً.
                </label>
                {error && <p className="text-red-600 text-sm mb-3">{error}</p>}
                <button
                  onClick={doDelete}
                  disabled={!confirm || busy}
                  className="w-full rounded-xl px-4 py-2.5 font-bold text-white bg-red-600 hover:bg-red-700 disabled:opacity-50"
                >
                  {busy ? "..." : "حذف حسابي نهائياً"}
                </button>
              </>
            ) : (
              <p className="text-muted text-sm">
                سجّل الدخول الأول من <a href="/login" className="text-teal underline">صفحة الدخول</a> عشان
                تقدر تحذف حسابك من هنا، أو احذفه من التطبيق أو بمراسلتنا.
              </p>
            )}
          </>
        )}
      </div>
    </div>
  );
}
