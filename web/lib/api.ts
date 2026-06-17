import { clearToken, getToken, setToken } from "./auth";

// نزيل أي BOM أو مسافات صفرية قد تتسرّب لقيمة متغيّر البيئة (مثلاً عند ضبطه عبر أنبوب PowerShell)،
// وإلا يصبح الرابط غير صالح ويُعامَل كمسار نسبي فتفشل كل نداءات الـ API.
const BASE = (process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000")
  .replace(/[﻿​]/g, "")
  .trim();

export class ApiError extends Error {
  status: number;
  detail: unknown;
  constructor(status: number, message: string, detail?: unknown) {
    super(message);
    this.status = status;
    this.detail = detail;
  }
}

function arabicError(status: number, detail: unknown): string {
  if (typeof detail === "string") return detail;
  if (detail && typeof detail === "object") {
    const d = detail as Record<string, unknown>;
    if (typeof d.message === "string") return d.message;
    if (Array.isArray(detail) && detail[0]?.msg) return String(detail[0].msg);
  }
  if (status === 401) return "بيانات الدخول غير صالحة. سجّل الدخول من جديد.";
  return "حصل خطأ. حاول تاني.";
}

async function req<T = unknown>(path: string, opts: RequestInit = {}): Promise<T> {
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
      /* ignore */
    }
    if (res.status === 401) clearToken();
    throw new ApiError(res.status, arabicError(res.status, detail), detail);
  }
  if (res.status === 204) return null as T;
  const ct = res.headers.get("content-type") || "";
  if (ct.includes("application/json")) return res.json();
  return (await res.blob()) as unknown as T;
}

const get = <T,>(p: string) => req<T>(p);
const post = <T,>(p: string, body?: unknown) =>
  req<T>(p, { method: "POST", body: body ? JSON.stringify(body) : undefined });
const put = <T,>(p: string, body?: unknown) =>
  req<T>(p, { method: "PUT", body: body ? JSON.stringify(body) : undefined });
const del = (p: string) => req<null>(p, { method: "DELETE" });

export const api = {
  // المصادقة
  async register(username: string, password: string) {
    const r = await post<{ access_token: string }>("/auth/register", { username, password });
    setToken(r.access_token);
    return r;
  },
  async login(username: string, password: string) {
    const r = await post<{ access_token: string }>("/auth/login", { username, password });
    setToken(r.access_token);
    return r;
  },
  me: () => get<any>("/auth/me"),

  // الملف الشخصي والأهداف
  getProfile: () => get<any>("/profile").catch((e) => {
    if (e instanceof ApiError && e.status === 404) return null;
    throw e;
  }),
  saveProfile: (b: any) => put<any>("/profile", b),
  targets: () => get<any>("/targets"),
  summary: (on?: string) => get<any>(`/summary${on ? `?on=${on}` : ""}`),
  bodyMetrics: () => get<any>("/metrics/body"),
  drinks: () => get<any[]>("/drinks/suggestions"),

  // الأكل
  foods: (on: string) => get<any[]>(`/foods?on=${on}`),
  addFood: (b: any) => post<any>("/foods", b),
  updateFood: (id: number, b: any) => put<any>(`/foods/${id}`, b),
  deleteFood: (id: number) => del(`/foods/${id}`),
  librarySearch: (q: string) => get<any[]>(`/foods/library/search?q=${encodeURIComponent(q)}`),
  estimate: (name: string, amount: number) =>
    get<any>(`/foods/estimate?name=${encodeURIComponent(name)}&amount=${amount}`),
  suggest: (q: string) => get<any[]>(`/foods/suggest?q=${encodeURIComponent(q)}`),
  barcode: (code: string) => get<any>(`/foods/barcode/${code}`),

  // الوصفات والمفضلة
  recipes: () => get<any[]>("/recipes"),
  createRecipe: (b: any) => post<any>("/recipes", b),
  logRecipe: (id: number, b: any) => post<any>(`/recipes/${id}/log`, b),
  deleteRecipe: (id: number) => del(`/recipes/${id}`),
  favorites: () => get<any[]>("/favorites"),
  addFavorite: (b: any) => post<any>("/favorites", b),
  logFavorite: (id: number, b: any) => post<any>(`/favorites/${id}/log`, b),
  deleteFavorite: (id: number) => del(`/favorites/${id}`),

  // المتابعة
  addWeight: (kg: number, date?: string) => post<any>("/weight", { weight_kg: kg, date }),
  weights: () => get<any[]>("/weight"),
  weightTrend: () => get<any>("/weight/trend"),
  addWaist: (cm: number) => post<any>("/waist", { waist_cm: cm }),
  waists: () => get<any[]>("/waist"),
  addWater: (ml: number) => post<any>("/water", { ml }),
  water: (on?: string) => get<any>(`/water${on ? `?on=${on}` : ""}`),
  addActivity: (b: any) => post<any>("/activity", b),
  activities: (on: string) => get<any[]>(`/activity?on=${on}`),
  deleteActivity: (id: number) => del(`/activity/${id}`),
  saveMood: (b: any) => put<any>("/mood", b),
  mood: (on?: string) => get<any>(`/mood${on ? `?on=${on}` : ""}`),

  // الإشراف (سوبر أدمن)
  adminUsers: (q?: string) =>
    get<any[]>(`/admin/users${q ? `?q=${encodeURIComponent(q)}` : ""}`),
  adminUser: (id: number) => get<any>(`/admin/users/${id}`),
  adminResetPassword: (id: number, newPassword: string) =>
    post<any>(`/admin/users/${id}/reset-password`, { new_password: newPassword }),
  adminSetAdmin: (id: number, isAdmin: boolean) =>
    post<any>(`/admin/users/${id}/admin`, { is_admin: isAdmin }),
  adminDeleteUser: (id: number) =>
    req<{ ok: boolean; message: string }>(`/admin/users/${id}`, { method: "DELETE" }),

  // التقارير
  weekly: (weekOf?: string) => get<any>(`/reports/weekly${weekOf ? `?week_of=${weekOf}` : ""}`),
  monthly: (year: number, month: number) => get<any>(`/reports/monthly?year=${year}&month=${month}`),
  weeklyPdf: (weekOf?: string) => get<Blob>(`/reports/weekly.pdf${weekOf ? `?week_of=${weekOf}` : ""}`),
  monthlyPdf: (year: number, month: number) => get<Blob>(`/reports/monthly.pdf?year=${year}&month=${month}`),
};

/** ينزّل blob كملف في المتصفح. */
export function downloadBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

export { BASE };
