"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { api, ApiError } from "@/lib/api";
import { Button, Field, PasswordField } from "@/components/ui";
import GoogleSignIn from "@/components/GoogleSignIn";

export default function LoginPage() {
  const router = useRouter();
  const [isLogin, setIsLogin] = useState(true);
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [email, setEmail] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function afterAuth() {
    const profile = await api.getProfile();
    router.replace(profile ? "/dashboard" : "/dashboard/profile");
  }

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
      else await api.register(username.trim(), password, email.trim() || undefined);
      await afterAuth();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "حصل خطأ. حاول تاني.");
    } finally {
      setBusy(false);
    }
  }

  async function onGoogle(idToken: string) {
    setBusy(true);
    setError(null);
    try {
      await api.googleLogin(idToken);
      await afterAuth();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "تعذّر تسجيل الدخول بجوجل.");
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
        <form onSubmit={submit} className="bg-surface rounded-2xl shadow-sm p-6">
          <Field
            label="اسم المستخدم"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            autoComplete="username"
          />
          <PasswordField
            label="كلمة السر"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoComplete={isLogin ? "current-password" : "new-password"}
          />
          {!isLogin && (
            <Field
              label="البريد الإلكتروني (اختياري — لاسترجاع كلمة السر)"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              autoComplete="email"
              placeholder="example@gmail.com"
            />
          )}
          {error && <p className="text-red-600 text-sm mb-3 text-center">{error}</p>}
          <Button type="submit" disabled={busy} className="w-full">
            {busy ? "..." : isLogin ? "دخول" : "إنشاء حساب"}
          </Button>

          {isLogin && (
            <div className="text-center mt-3">
              <Link href="/forgot-password" className="text-teal text-sm">
                نسيت كلمة السر؟
              </Link>
            </div>
          )}

          <GoogleSignIn onCredential={onGoogle} onError={(m) => setError(m)} />

          <button
            type="button"
            onClick={() => {
              setIsLogin(!isLogin);
              setError(null);
            }}
            className="w-full mt-4 text-teal text-sm"
          >
            {isLogin ? "معندكش حساب؟ سجّل دلوقتي" : "عندك حساب؟ سجّل دخول"}
          </button>
        </form>
      </div>
    </div>
  );
}
