"use client";
import React, { useState } from "react";

export function Card({ children, className = "" }: { children: React.ReactNode; className?: string }) {
  return <div className={`bg-white rounded-2xl shadow-sm p-5 ${className}`}>{children}</div>;
}

export function Button({
  children,
  onClick,
  type = "button",
  variant = "primary",
  disabled,
  className = "",
}: {
  children: React.ReactNode;
  onClick?: () => void;
  type?: "button" | "submit";
  variant?: "primary" | "outline" | "danger";
  disabled?: boolean;
  className?: string;
}) {
  const styles = {
    primary: "bg-teal text-white hover:bg-teal-dark",
    outline: "border border-teal text-teal hover:bg-teal/5",
    danger: "border border-red-500 text-red-600 hover:bg-red-50",
  }[variant];
  return (
    <button
      type={type}
      onClick={onClick}
      disabled={disabled}
      className={`rounded-xl px-4 py-2.5 font-bold transition disabled:opacity-50 ${styles} ${className}`}
    >
      {children}
    </button>
  );
}

export function Field({
  label,
  ...props
}: { label: string } & React.InputHTMLAttributes<HTMLInputElement>) {
  return (
    <label className="block mb-3">
      <span className="block mb-1 text-sm text-muted">{label}</span>
      <input
        {...props}
        className="w-full rounded-xl border border-gray-200 bg-white px-4 py-2.5 outline-none focus:border-teal"
      />
    </label>
  );
}

export function PasswordField({
  label,
  ...props
}: { label: string } & React.InputHTMLAttributes<HTMLInputElement>) {
  const [show, setShow] = useState(false);
  return (
    <label className="block mb-3">
      <span className="block mb-1 text-sm text-muted">{label}</span>
      <div className="relative">
        <input
          {...props}
          type={show ? "text" : "password"}
          className="w-full rounded-xl border border-gray-200 bg-white px-4 py-2.5 pe-11 outline-none focus:border-teal"
        />
        <button
          type="button"
          tabIndex={-1}
          onClick={() => setShow((s) => !s)}
          aria-label={show ? "إخفاء كلمة السر" : "إظهار كلمة السر"}
          aria-pressed={show}
          className="absolute inset-y-0 end-0 flex items-center px-3 text-muted hover:text-teal transition"
        >
          {show ? (
            // eye-off
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M9.88 9.88a3 3 0 1 0 4.24 4.24" />
              <path d="M10.73 5.08A10.43 10.43 0 0 1 12 5c7 0 10 7 10 7a13.16 13.16 0 0 1-1.67 2.68" />
              <path d="M6.61 6.61A13.526 13.526 0 0 0 2 12s3 7 10 7a9.74 9.74 0 0 0 5.39-1.61" />
              <line x1="2" y1="2" x2="22" y2="22" />
            </svg>
          ) : (
            // eye
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M2 12s3-7 10-7 10 7 10 7-3 7-10 7-10-7-10-7Z" />
              <circle cx="12" cy="12" r="3" />
            </svg>
          )}
        </button>
      </div>
    </label>
  );
}

export function Select({
  label,
  children,
  ...props
}: { label: string } & React.SelectHTMLAttributes<HTMLSelectElement>) {
  return (
    <label className="block mb-3">
      <span className="block mb-1 text-sm text-muted">{label}</span>
      <select
        {...props}
        className="w-full rounded-xl border border-gray-200 bg-white px-4 py-2.5 outline-none focus:border-teal"
      >
        {children}
      </select>
    </label>
  );
}

export function StatRow({ k, v }: { k: string; v: React.ReactNode }) {
  return (
    <div className="flex justify-between py-1.5 border-b border-gray-50 last:border-0">
      <span className="text-muted">{k}</span>
      <span className="font-bold">{v}</span>
    </div>
  );
}

export function Spinner() {
  return (
    <div className="grid place-items-center py-10">
      <div className="h-8 w-8 animate-spin rounded-full border-4 border-teal/20 border-t-teal" />
    </div>
  );
}

export function Bar({ label, eaten, target, color }: { label: string; eaten: number; target: number; color: string }) {
  const pct = target > 0 ? Math.min((eaten / target) * 100, 100) : 0;
  return (
    <div className="py-1.5">
      <div className="flex justify-between text-sm mb-1">
        <span className="font-semibold">{label}</span>
        <span className="text-muted">
          {Math.round(eaten)} / {Math.round(target)} جم
        </span>
      </div>
      <div className="h-2.5 rounded-full bg-gray-100 overflow-hidden">
        <div className="h-full rounded-full" style={{ width: `${pct}%`, background: color }} />
      </div>
    </div>
  );
}
