"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { api, ApiError } from "@/lib/api";
import { Button, Field } from "@/components/ui";

export default function LoginPage() {
  const router = useRouter();
  const [isLogin, setIsLogin] = useState(true);
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (username.trim().length < 3 || password.length < 6) {
      setError("اسم المستخدم 3 أحرف على الأقل وكلمة السر 6 على الأقل.");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      if (isLogin) await api.login(username.trim(), password);
      else await api.register(username.trim(), password);
      const profile = await api.getProfile();
      router.replace(profile ? "/dashboard" : "/dashboard/profile");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "حصل خطأ. حاول تاني.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="min-h-screen grid place-items-center px-4">
      <div className="w-full max-w-sm">
        <div className="text-center mb-8">
          <div className="text-5xl">🥗</div>
          <h1 className="text-3xl font-extrabold text-teal mt-2">رشاقة</h1>
          <p className="text-muted mt-1">لوحة تحكم التخسيس الصحي</p>
        </div>
        <form onSubmit={submit} className="bg-white rounded-2xl shadow-sm p-6">
          <Field
            label="اسم المستخدم"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            autoComplete="username"
          />
          <Field
            label="كلمة السر"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoComplete={isLogin ? "current-password" : "new-password"}
          />
          {error && <p className="text-red-600 text-sm mb-3 text-center">{error}</p>}
          <Button type="submit" disabled={busy} className="w-full">
            {busy ? "..." : isLogin ? "دخول" : "إنشاء حساب"}
          </Button>
          <button
            type="button"
            onClick={() => setIsLogin(!isLogin)}
            className="w-full mt-3 text-teal text-sm"
          >
            {isLogin ? "معندكش حساب؟ سجّل دلوقتي" : "عندك حساب؟ سجّل دخول"}
          </button>
        </form>
      </div>
    </div>
  );
}
