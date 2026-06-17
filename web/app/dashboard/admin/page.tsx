"use client";
import { useEffect, useState } from "react";
import { api, ApiError } from "@/lib/api";
import { Button, Card, Field, Spinner, StatRow } from "@/components/ui";

type UserRow = {
  id: number;
  username: string;
  is_admin: boolean;
  created_at: string;
  has_profile: boolean;
  current_weight_kg: number | null;
  goal_weight_kg: number | null;
  target_calories: number | null;
  foods_count: number;
  weights_count: number;
  last_food_date: string | null;
};

function fmtDate(s?: string | null) {
  if (!s) return "—";
  try {
    return new Date(s).toLocaleDateString("ar-EG", { year: "numeric", month: "short", day: "numeric" });
  } catch {
    return s;
  }
}

export default function AdminPage() {
  const [loading, setLoading] = useState(true);
  const [forbidden, setForbidden] = useState(false);
  const [users, setUsers] = useState<UserRow[]>([]);
  const [q, setQ] = useState("");
  const [selected, setSelected] = useState<any | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [msg, setMsg] = useState<string>("");
  const [meId, setMeId] = useState<number | null>(null);

  async function load(query = "") {
    setLoading(true);
    try {
      const [list, me] = await Promise.all([api.adminUsers(query), api.me()]);
      setUsers(list as UserRow[]);
      setMeId(me?.id ?? null);
      setForbidden(false);
    } catch (e) {
      if (e instanceof ApiError && e.status === 403) setForbidden(true);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  async function openDetail(id: number) {
    setDetailLoading(true);
    setSelected(null);
    try {
      setSelected(await api.adminUser(id));
    } catch {
      setMsg("تعذّر تحميل التفاصيل.");
    } finally {
      setDetailLoading(false);
    }
  }

  function flash(m: string) {
    setMsg(m);
    setTimeout(() => setMsg(""), 4000);
  }

  async function resetPassword(u: { id: number; username: string }) {
    const pw = window.prompt(`كلمة سر جديدة للمستخدم "${u.username}" (٦ أحرف على الأقل):`);
    if (!pw) return;
    if (pw.length < 6) return flash("كلمة السر لازم ٦ أحرف على الأقل.");
    try {
      const r = await api.adminResetPassword(u.id, pw);
      flash(r?.message || "تم تغيير كلمة السر.");
    } catch (e) {
      flash(e instanceof ApiError ? e.message : "فشل تغيير كلمة السر.");
    }
  }

  async function toggleAdmin(u: { id: number; username: string; is_admin: boolean }) {
    const next = !u.is_admin;
    if (!window.confirm(`${next ? "منح" : "سحب"} صلاحية الإشراف للمستخدم "${u.username}"؟`)) return;
    try {
      const r = await api.adminSetAdmin(u.id, next);
      flash(r?.message || "تم.");
      await load(q);
      if (selected?.id === u.id) await openDetail(u.id);
    } catch (e) {
      flash(e instanceof ApiError ? e.message : "فشل تعديل الصلاحية.");
    }
  }

  async function deleteUser(u: { id: number; username: string }) {
    if (!window.confirm(`حذف المستخدم "${u.username}" وكل بياناته نهائياً؟ لا يمكن التراجع.`)) return;
    try {
      const r = await api.adminDeleteUser(u.id);
      flash(r?.message || "تم الحذف.");
      setSelected(null);
      await load(q);
    } catch (e) {
      flash(e instanceof ApiError ? e.message : "فشل الحذف.");
    }
  }

  if (loading) return <Spinner />;

  if (forbidden)
    return (
      <Card>
        <div className="text-center py-8">
          <div className="text-3xl mb-2">🛡️</div>
          <div className="font-bold text-lg mb-1">هذه الصفحة للمشرفين فقط</div>
          <div className="text-muted text-sm">حسابك ليس لديه صلاحية الإشراف.</div>
        </div>
      </Card>
    );

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between flex-wrap gap-2">
        <h1 className="text-2xl font-extrabold">🛡️ الإشراف — المستخدمون ({users.length})</h1>
      </div>

      {msg && (
        <div className="rounded-xl bg-teal/10 text-teal px-4 py-2.5 text-sm font-semibold">{msg}</div>
      )}

      <Card>
        <div className="flex gap-2 mb-4">
          <input
            value={q}
            onChange={(e) => setQ(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && load(q)}
            placeholder="ابحث باسم المستخدم…"
            className="flex-1 rounded-xl border border-gray-200 bg-white px-4 py-2.5 outline-none focus:border-teal"
          />
          <Button onClick={() => load(q)}>بحث</Button>
        </div>

        <div className="overflow-x-auto -mx-2">
          <table className="w-full text-sm min-w-[640px]">
            <thead>
              <tr className="text-muted text-right border-b border-gray-100">
                <th className="py-2 px-2 font-semibold">المستخدم</th>
                <th className="py-2 px-2 font-semibold">الهدف (سعرات)</th>
                <th className="py-2 px-2 font-semibold">الوزن</th>
                <th className="py-2 px-2 font-semibold">وجبات</th>
                <th className="py-2 px-2 font-semibold">آخر تسجيل</th>
                <th className="py-2 px-2 font-semibold">إجراءات</th>
              </tr>
            </thead>
            <tbody>
              {users.map((u) => (
                <tr key={u.id} className="border-b border-gray-50 hover:bg-gray-50">
                  <td className="py-2 px-2">
                    <button onClick={() => openDetail(u.id)} className="font-bold text-teal hover:underline">
                      {u.username}
                    </button>
                    {u.is_admin && (
                      <span className="ms-2 text-[11px] bg-amber-100 text-amber-700 rounded px-1.5 py-0.5">
                        مشرف
                      </span>
                    )}
                    {!u.has_profile && <span className="ms-2 text-[11px] text-muted">(بدون ملف)</span>}
                  </td>
                  <td className="py-2 px-2">{u.target_calories ?? "—"}</td>
                  <td className="py-2 px-2">{u.current_weight_kg ?? "—"}</td>
                  <td className="py-2 px-2">{u.foods_count}</td>
                  <td className="py-2 px-2">{fmtDate(u.last_food_date)}</td>
                  <td className="py-2 px-2">
                    <div className="flex gap-1.5 flex-wrap">
                      <button
                        onClick={() => resetPassword(u)}
                        className="text-xs rounded-lg border border-teal text-teal px-2 py-1 hover:bg-teal/5"
                      >
                        كلمة سر
                      </button>
                      <button
                        onClick={() => toggleAdmin(u)}
                        className="text-xs rounded-lg border border-amber-500 text-amber-600 px-2 py-1 hover:bg-amber-50"
                      >
                        {u.is_admin ? "إلغاء إشراف" : "إشراف"}
                      </button>
                      {u.id !== meId && (
                        <button
                          onClick={() => deleteUser(u)}
                          className="text-xs rounded-lg border border-red-500 text-red-600 px-2 py-1 hover:bg-red-50"
                        >
                          حذف
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
              {users.length === 0 && (
                <tr>
                  <td colSpan={6} className="py-6 text-center text-muted">
                    لا يوجد مستخدمون.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </Card>

      {detailLoading && <Spinner />}

      {selected && (
        <Card>
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-xl font-extrabold">
              👤 {selected.username} {selected.is_admin && <span className="text-sm text-amber-600">(مشرف)</span>}
            </h2>
            <button onClick={() => setSelected(null)} className="text-muted hover:text-ink">
              ✕ إغلاق
            </button>
          </div>

          <div className="grid md:grid-cols-2 gap-4">
            <div>
              <div className="font-bold mb-2 text-muted">الملف الشخصي</div>
              {selected.profile ? (
                <>
                  <StatRow k="العمر" v={selected.profile.age ?? "—"} />
                  <StatRow k="النوع" v={selected.profile.sex === "male" ? "ذكر" : selected.profile.sex === "female" ? "أنثى" : "—"} />
                  <StatRow k="الطول" v={`${selected.profile.height_cm ?? "—"} سم`} />
                  <StatRow k="الوزن" v={`${selected.profile.weight_kg ?? "—"} كجم`} />
                  <StatRow k="الوزن المستهدف" v={selected.profile.goal_weight_kg ? `${selected.profile.goal_weight_kg} كجم` : "—"} />
                  <StatRow k="هدف السعرات" v={selected.target_calories ?? "—"} />
                  <StatRow k="BMI" v={selected.bmi ?? "—"} />
                </>
              ) : (
                <div className="text-muted text-sm">لم يُكمل ملفه الشخصي بعد.</div>
              )}
              <StatRow k="تاريخ التسجيل" v={fmtDate(selected.created_at)} />
              <StatRow k="عدد الوجبات" v={selected.foods_count} />
              <StatRow k="عدد قياسات الوزن" v={selected.weights_count} />
            </div>

            <div>
              <div className="font-bold mb-2 text-muted">آخر الوجبات</div>
              {selected.recent_foods?.length ? (
                <ul className="text-sm space-y-1 mb-4">
                  {selected.recent_foods.map((f: any, i: number) => (
                    <li key={i} className="flex justify-between border-b border-gray-50 py-1">
                      <span>{f.name_ar} <span className="text-muted">({f.amount}جم)</span></span>
                      <span className="text-muted">{Math.round(f.calories)} سعرة · {fmtDate(f.date)}</span>
                    </li>
                  ))}
                </ul>
              ) : (
                <div className="text-muted text-sm mb-4">لا توجد وجبات مسجّلة.</div>
              )}
              <div className="font-bold mb-2 text-muted">آخر قياسات الوزن</div>
              {selected.recent_weights?.length ? (
                <ul className="text-sm space-y-1">
                  {selected.recent_weights.map((w: any, i: number) => (
                    <li key={i} className="flex justify-between border-b border-gray-50 py-1">
                      <span>{w.weight_kg} كجم</span>
                      <span className="text-muted">{fmtDate(w.date)}</span>
                    </li>
                  ))}
                </ul>
              ) : (
                <div className="text-muted text-sm">لا توجد قياسات.</div>
              )}
            </div>
          </div>

          <div className="flex gap-2 mt-5 flex-wrap border-t border-gray-100 pt-4">
            <Button variant="outline" onClick={() => resetPassword(selected)}>
              🔑 تغيير كلمة السر
            </Button>
            <Button variant="outline" onClick={() => toggleAdmin(selected)}>
              {selected.is_admin ? "سحب الإشراف" : "منح الإشراف"}
            </Button>
            {selected.id !== meId && (
              <Button variant="danger" onClick={() => deleteUser(selected)}>
                🗑️ حذف المستخدم
              </Button>
            )}
          </div>
        </Card>
      )}
    </div>
  );
}
