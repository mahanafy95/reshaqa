"use client";
import { useEffect, useState } from "react";
import { api, ApiError, BASE } from "@/lib/api";
import { getToken } from "@/lib/auth";
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
  is_premium: boolean;
  foods_count: number;
  weights_count: number;
  last_food_date: string | null;
};

type IssueStatus = "new" | "seen" | "resolved";

type IssueRow = {
  id: number;
  user_id: number;
  username: string;
  message: string;
  context: string | null;
  status: IssueStatus;
  created_at: string;
};

// نداءات بلاغات المشاكل: لا توجد لها دوال في مساعد الـ api، فنستخدم نفس نمط الجلب
// (نفس الـ BASE وترويسة المصادقة Bearer) المستخدَم في lib/api.ts.
async function issuesReq<T = unknown>(path: string, opts: RequestInit = {}): Promise<T> {
  const token = getToken();
  const res = await fetch(`${BASE}${path}`, {
    ...opts,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(opts.headers || {}),
    },
  });
  if (!res.ok) {
    let detail: unknown;
    try {
      detail = (await res.json()).detail;
    } catch {
      /* تجاهل */
    }
    const message = typeof detail === "string" ? detail : "حصل خطأ. حاول تاني.";
    throw new ApiError(res.status, message, detail);
  }
  if (res.status === 204) return null as T;
  return res.json();
}

const ISSUE_STATUS_AR: Record<IssueStatus, string> = {
  new: "جديد",
  seen: "تمت المشاهدة",
  resolved: "تم الحل",
};

const ISSUE_STATUS_BADGE: Record<IssueStatus, string> = {
  new: "bg-red-100 text-red-700",
  seen: "bg-amber-100 text-amber-700",
  resolved: "bg-teal/15 text-teal",
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
  const [showAdd, setShowAdd] = useState(false);
  const [addForm, setAddForm] = useState({ username: "", password: "", is_admin: false });
  const [adding, setAdding] = useState(false);
  const [issues, setIssues] = useState<IssueRow[]>([]);
  const [issuesLoading, setIssuesLoading] = useState(true);
  const [issueBusy, setIssueBusy] = useState<number | null>(null);

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

  async function loadIssues() {
    setIssuesLoading(true);
    try {
      const list = await issuesReq<IssueRow[]>("/issues");
      setIssues(list);
    } catch {
      /* لو مفيش صلاحية أو فشل الجلب، نسيب القائمة فاضية */
    } finally {
      setIssuesLoading(false);
    }
  }

  async function setIssueStatus(id: number, status: IssueStatus) {
    setIssueBusy(id);
    try {
      const updated = await issuesReq<IssueRow>(`/issues/${id}`, {
        method: "PATCH",
        body: JSON.stringify({ status }),
      });
      setIssues((prev) => prev.map((it) => (it.id === id ? updated : it)));
    } catch (e) {
      flash(e instanceof ApiError ? e.message : "فشل تحديث حالة البلاغ.");
    } finally {
      setIssueBusy(null);
    }
  }

  useEffect(() => {
    load();
    loadIssues();
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

  async function createUser() {
    if (addForm.username.trim().length < 3) return flash("اسم المستخدم لازم ٣ أحرف على الأقل.");
    if (addForm.password.length < 6) return flash("كلمة السر لازم ٦ أحرف على الأقل.");
    setAdding(true);
    try {
      await api.adminCreateUser({
        username: addForm.username.trim(),
        password: addForm.password,
        is_admin: addForm.is_admin,
      });
      flash(`تم إضافة المستخدم ${addForm.username.trim()}.`);
      setAddForm({ username: "", password: "", is_admin: false });
      setShowAdd(false);
      await load(q);
    } catch (e) {
      flash(e instanceof ApiError ? e.message : "فشل إضافة المستخدم.");
    } finally {
      setAdding(false);
    }
  }

  const TEST_RE =
    /^(test_|qa_|hc_|deploychk|deploycheck|verifychk|finalchk|guardchk|envtest|zz_qa|paneltest|healthchk|spam|brute|ratelimit|abuse|rl_)/i;

  async function bulkDeleteTargets(targets: UserRow[], label: string) {
    if (!targets.length) return flash(`مفيش حسابات ${label} للحذف.`);
    const sample = targets.slice(0, 6).map((u) => u.username).join("، ");
    if (
      !window.confirm(
        `حذف ${targets.length} حساب نهائياً؟\nأمثلة: ${sample}${targets.length > 6 ? " …" : ""}\n(حساباتك والمشرفين مش هيتمسحوا)`
      )
    )
      return;
    try {
      const r = await api.adminBulkDelete(targets.map((u) => u.id));
      flash(`تم حذف ${r.deleted} حساب${r.skipped ? ` (تم تخطّي ${r.skipped})` : ""}.`);
      setSelected(null);
      await load(q);
    } catch (e) {
      flash(e instanceof ApiError ? e.message : "فشل الحذف.");
    }
  }

  async function cleanupTestUsers() {
    const targets = users.filter((u) => TEST_RE.test(u.username) && !u.is_admin && u.id !== meId);
    await bulkDeleteTargets(targets, "تجريبية");
  }

  async function cleanupByPrefix() {
    const prefix = window.prompt("اكتب بداية اسم الحسابات اللي تحب تمسحها (مثلاً Spam):", "Spam");
    if (!prefix || !prefix.trim()) return;
    const p = prefix.trim().toLowerCase();
    const targets = users.filter(
      (u) => u.username.toLowerCase().startsWith(p) && !u.is_admin && u.id !== meId
    );
    await bulkDeleteTargets(targets, `تبدأ بـ "${prefix.trim()}"`);
  }

  async function renameUser(u: { id: number; username: string }) {
    const name = window.prompt(`اسم جديد للمستخدم "${u.username}" (٣ أحرف على الأقل، بدون مسافات):`, u.username);
    if (!name || name.trim() === u.username) return;
    try {
      const r = await api.adminRenameUser(u.id, name.trim());
      flash(r?.message || "تم تغيير الاسم.");
      await load(q);
      if (selected?.id === u.id) await openDetail(u.id);
    } catch (e) {
      flash(e instanceof ApiError ? e.message : "فشل تغيير الاسم.");
    }
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

  async function togglePremium(u: { id: number; username: string; is_premium: boolean }) {
    if (u.is_premium) {
      if (!window.confirm(`سحب Premium من المستخدم "${u.username}"؟`)) return;
      try {
        const r = await api.adminSetPremium(u.id, false);
        flash(r?.message || "تم سحب Premium.");
        await load(q);
        if (selected?.id === u.id) await openDetail(u.id);
      } catch (e) {
        flash(e instanceof ApiError ? e.message : "فشل.");
      }
      return;
    }
    const ans = window.prompt(
      `منح Premium مجاناً للمستخدم "${u.username}".\nكام يوم؟ (سيبها فاضية = بلا انتهاء)`,
      ""
    );
    if (ans === null) return;
    const days = ans.trim() === "" ? null : Number(ans.trim());
    if (days !== null && (!Number.isFinite(days) || days < 1)) return flash("عدد أيام غير صالح.");
    try {
      const r = await api.adminSetPremium(u.id, true, days);
      flash(r?.message || "تم منح Premium.");
      await load(q);
      if (selected?.id === u.id) await openDetail(u.id);
    } catch (e) {
      flash(e instanceof ApiError ? e.message : "فشل منح Premium.");
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
        <div className="flex gap-2 flex-wrap">
          <Button variant="danger" onClick={cleanupTestUsers}>🧹 حذف الحسابات التجريبية</Button>
          <Button variant="outline" onClick={cleanupByPrefix}>✂️ حذف بادئة…</Button>
          <Button onClick={() => setShowAdd((s) => !s)}>{showAdd ? "✕ إلغاء" : "➕ إضافة مستخدم"}</Button>
        </div>
      </div>

      {msg && (
        <div className="rounded-xl bg-teal/10 text-teal px-4 py-2.5 text-sm font-semibold">{msg}</div>
      )}

      {showAdd && (
        <Card>
          <h2 className="font-bold text-lg mb-3">➕ إضافة مستخدم جديد</h2>
          <div className="grid md:grid-cols-2 gap-3">
            <Field
              label="اسم المستخدم"
              value={addForm.username}
              onChange={(e) => setAddForm({ ...addForm, username: e.target.value })}
              placeholder="بدون مسافات، ٣ أحرف على الأقل"
            />
            <Field
              label="كلمة السر"
              type="text"
              value={addForm.password}
              onChange={(e) => setAddForm({ ...addForm, password: e.target.value })}
              placeholder="٦ أحرف على الأقل"
            />
          </div>
          <label className="flex items-center gap-2 mb-3 text-sm">
            <input
              type="checkbox"
              checked={addForm.is_admin}
              onChange={(e) => setAddForm({ ...addForm, is_admin: e.target.checked })}
            />
            <span>يكون مشرفاً (صلاحية كاملة)</span>
          </label>
          <Button onClick={createUser} disabled={adding}>
            {adding ? "جارٍ الإضافة…" : "حفظ المستخدم"}
          </Button>
        </Card>
      )}

      <Card>
        <div className="flex gap-2 mb-4">
          <input
            value={q}
            onChange={(e) => setQ(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && load(q)}
            placeholder="ابحث باسم المستخدم…"
            className="flex-1 rounded-xl border border-line bg-surface px-4 py-2.5 outline-none focus:border-teal"
          />
          <Button onClick={() => load(q)}>بحث</Button>
        </div>

        <div className="overflow-x-auto -mx-2">
          <table className="w-full text-sm min-w-[640px]">
            <thead>
              <tr className="text-muted text-right border-b border-line">
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
                <tr key={u.id} className="border-b border-line hover:bg-soft">
                  <td className="py-2 px-2">
                    <button onClick={() => openDetail(u.id)} className="font-bold text-teal hover:underline">
                      {u.username}
                    </button>
                    {u.is_admin && (
                      <span className="ms-2 text-[11px] bg-amber-100 text-amber-700 rounded px-1.5 py-0.5">
                        مشرف
                      </span>
                    )}
                    {u.is_premium && (
                      <span className="ms-2 text-[11px] bg-teal/15 text-teal rounded px-1.5 py-0.5">
                        💎 Premium
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
                        onClick={() => renameUser(u)}
                        className="text-xs rounded-lg border border-line text-ink px-2 py-1 hover:bg-soft"
                      >
                        الاسم
                      </button>
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
                      <button
                        onClick={() => togglePremium(u)}
                        className="text-xs rounded-lg border border-teal text-teal px-2 py-1 hover:bg-teal/5"
                      >
                        {u.is_premium ? "سحب Premium" : "منح Premium"}
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

      <Card>
        <h2 className="font-bold text-lg mb-4">
          🐞 بلاغات المشاكل{" "}
          <span className="text-muted font-normal text-base">({issues.length})</span>
        </h2>

        {issuesLoading ? (
          <Spinner />
        ) : issues.length === 0 ? (
          <div className="py-6 text-center text-muted text-sm">لا توجد بلاغات حالياً.</div>
        ) : (
          <ul className="space-y-3">
            {issues.map((it) => (
              <li
                key={it.id}
                className={`rounded-xl border p-4 ${
                  it.status === "new"
                    ? "border-red-200 bg-red-50/60"
                    : "border-line bg-surface"
                }`}
              >
                <div className="flex items-start justify-between gap-3 flex-wrap mb-2">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="font-bold text-ink">{it.username}</span>
                    <span
                      className={`text-[11px] rounded px-1.5 py-0.5 font-semibold ${ISSUE_STATUS_BADGE[it.status]}`}
                    >
                      {ISSUE_STATUS_AR[it.status]}
                    </span>
                  </div>
                  <span className="text-xs text-muted">{fmtDate(it.created_at)}</span>
                </div>

                <p className="text-sm text-ink whitespace-pre-wrap break-words mb-2">
                  {it.message}
                </p>

                {it.context && (
                  <div className="text-xs text-muted mb-3">السياق: {it.context}</div>
                )}

                <div className="flex gap-1.5 flex-wrap">
                  <button
                    onClick={() => setIssueStatus(it.id, "seen")}
                    disabled={issueBusy === it.id || it.status === "seen"}
                    className="text-xs rounded-lg border border-amber-500 text-amber-600 px-2 py-1 hover:bg-amber-50 disabled:opacity-50"
                  >
                    تمت المشاهدة
                  </button>
                  <button
                    onClick={() => setIssueStatus(it.id, "resolved")}
                    disabled={issueBusy === it.id || it.status === "resolved"}
                    className="text-xs rounded-lg border border-teal text-teal px-2 py-1 hover:bg-teal/5 disabled:opacity-50"
                  >
                    تم الحل
                  </button>
                </div>
              </li>
            ))}
          </ul>
        )}
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
                    <li key={i} className="flex justify-between border-b border-line py-1">
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
                    <li key={i} className="flex justify-between border-b border-line py-1">
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

          <div className="flex gap-2 mt-5 flex-wrap border-t border-line pt-4">
            <Button variant="outline" onClick={() => renameUser(selected)}>
              ✏️ تغيير الاسم
            </Button>
            <Button variant="outline" onClick={() => resetPassword(selected)}>
              🔑 تغيير كلمة السر
            </Button>
            <Button variant="outline" onClick={() => toggleAdmin(selected)}>
              {selected.is_admin ? "سحب الإشراف" : "منح الإشراف"}
            </Button>
            <Button variant="outline" onClick={() => togglePremium(selected)}>
              {selected.is_premium ? "💎 سحب Premium" : "💎 منح Premium"}
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
