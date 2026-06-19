"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { api, ApiError } from "@/lib/api";
import { Button, Field, PasswordField } from "@/components/ui";

export default function ForgotPasswordPage() {
  const router = useRouter();
  const [step, setStep] = useState<1 | 2>(1);
  const [email, setEmail] = useState("");
  const [code, setCode] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [info, setInfo] = useState<string | null>(null);

  async function requestCode(e: React.FormEvent) {
    e.preventDefault();
    if (!email.trim()) {
      setError("اكتب بريدك الإلكتروني.");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const r = await api.forgotPassword(email.trim());
      setInfo(r.message);
      setStep(2);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "حصل خطأ. حاول تاني.");
    } finally {
      setBusy(false);
    }
  }

  async function doReset(e: React.FormEvent) {
    e.preventDefault();
    if (code.trim().length < 4 || newPassword.length < 6) {
      setError("اكتب الرمز وكلمة سر جديدة (6 أحرف على الأقل).");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      await api.resetPassword(email.trim(), code.trim(), newPassword);
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
          <div className="text-5xl">🔑</div>
          <h1 className="text-2xl font-extrabold text-teal mt-2">استرجاع كلمة السر</h1>
          <p className="text-muted mt-1 text-sm">
            {step === 1
              ? "هنبعتلك رمز على إيميلك"
              : "اكتب الرمز اللي وصلك وكلمة سر جديدة"}
          </p>
        </div>

        {step === 1 ? (
          <form onSubmit={requestCode} className="bg-surface rounded-2xl shadow-sm p-6">
            <Field
              label="البريد الإلكتروني"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              autoComplete="email"
              placeholder="example@gmail.com"
            />
            {error && <p className="text-red-600 text-sm mb-3 text-center">{error}</p>}
            <Button type="submit" disabled={busy} className="w-full">
              {busy ? "..." : "ابعت الرمز"}
            </Button>
          </form>
        ) : (
          <form onSubmit={doReset} className="bg-surface rounded-2xl shadow-sm p-6">
            {info && <p className="text-teal text-sm mb-3 text-center">{info}</p>}
            <Field
              label="الرمز (6 أرقام)"
              inputMode="numeric"
              value={code}
              onChange={(e) => setCode(e.target.value)}
              placeholder="123456"
            />
            <PasswordField
              label="كلمة السر الجديدة"
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              autoComplete="new-password"
            />
            {error && <p className="text-red-600 text-sm mb-3 text-center">{error}</p>}
            <Button type="submit" disabled={busy} className="w-full">
              {busy ? "..." : "غيّر كلمة السر وادخل"}
            </Button>
            <button
              type="button"
              onClick={() => {
                setStep(1);
                setError(null);
                setInfo(null);
              }}
              className="w-full mt-3 text-teal text-sm"
            >
              مطلعش الرمز؟ ابعت تاني
            </button>
          </form>
        )}

        <div className="text-center mt-4">
          <Link href="/login" className="text-teal text-sm">
            رجوع لتسجيل الدخول
          </Link>
        </div>
      </div>
    </div>
  );
}
