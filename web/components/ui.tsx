"use client";
import React from "react";

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
