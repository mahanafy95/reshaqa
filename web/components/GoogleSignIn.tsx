"use client";
import { useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";

// معرّف عميل جوجل (الويب). الأولوية لمتغيّر بيئة Vercel (أسرع، بدون نداء شبكة)،
// وإلا نجيبه من الخادم /auth/config، فيتفعّل الزر بمجرّد ضبط الخادم بدون إعادة بناء.
// لو الاتنين فاضيين، الزر يختفي ويفضل الدخول بكلمة السر شغّال عادي.
const ENV_CLIENT_ID = (process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID || "")
  .replace(/[﻿​]/g, "")
  .trim();

declare global {
  interface Window {
    google?: any;
  }
}

/**
 * زر "تسجيل الدخول بجوجل" باستخدام Google Identity Services (مجاني).
 * عند نجاح المصادقة يستدعي oncredential ومعها الـ ID token.
 */
export default function GoogleSignIn({
  onCredential,
  onError,
}: {
  onCredential: (idToken: string) => void;
  onError?: (msg: string) => void;
}) {
  const btnRef = useRef<HTMLDivElement>(null);
  const [clientId, setClientId] = useState<string>(ENV_CLIENT_ID);
  const [ready, setReady] = useState(false);

  // لو مفيش معرّف من متغيّر البيئة، نجيبه من الخادم
  useEffect(() => {
    if (clientId) return;
    let alive = true;
    api
      .authConfig()
      .then((c) => {
        if (alive && c?.google_login_enabled && c?.google_client_id) {
          setClientId(c.google_client_id.replace(/[﻿​]/g, "").trim());
        }
      })
      .catch(() => {});
    return () => {
      alive = false;
    };
  }, [clientId]);

  useEffect(() => {
    if (!clientId) return; // غير مضبوط — لا نعرض شيئاً

    function init() {
      if (!window.google?.accounts?.id || !btnRef.current) return;
      try {
        window.google.accounts.id.initialize({
          client_id: clientId,
          callback: (resp: { credential?: string }) => {
            if (resp?.credential) onCredential(resp.credential);
            else onError?.("تعذّر تسجيل الدخول بجوجل. حاول تاني.");
          },
        });
        window.google.accounts.id.renderButton(btnRef.current, {
          theme: "outline",
          size: "large",
          width: 320,
          text: "continue_with",
          shape: "pill",
          locale: "ar",
        });
        setReady(true);
      } catch {
        onError?.("تعذّر تحميل تسجيل الدخول بجوجل.");
      }
    }

    // حمّل سكربت GIS مرة واحدة
    const existing = document.getElementById("gsi-script") as HTMLScriptElement | null;
    if (existing) {
      if (window.google?.accounts?.id) init();
      else existing.addEventListener("load", init);
    } else {
      const s = document.createElement("script");
      s.id = "gsi-script";
      s.src = "https://accounts.google.com/gsi/client";
      s.async = true;
      s.defer = true;
      s.onload = init;
      document.body.appendChild(s);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [clientId]);

  if (!clientId) return null;

  return (
    <div className="mt-4">
      <div className="flex items-center gap-3 mb-3">
        <div className="h-px flex-1 bg-gray-200" />
        <span className="text-xs text-muted">أو</span>
        <div className="h-px flex-1 bg-gray-200" />
      </div>
      <div className="flex justify-center" ref={btnRef} />
      {!ready && <p className="text-center text-xs text-muted mt-2">جاري تحميل زر جوجل…</p>}
    </div>
  );
}
