"use client";

import React from "react";
import Card from "@/components/ui/Card";
import Icon from "@/components/ui/Icon";

interface Props {
  label: string;
  value: string;
  sub?: React.ReactNode;
  icon: string;
  tint?: string;
  delta?: number | null;
  deltaLabel?: string;
  progressPercent?: number;
  progressBarColor?: string;
  children?: React.ReactNode;
  onClick?: () => void;
}

export default function KpiCard({
  label,
  value,
  sub,
  icon,
  tint = "",
  delta,
  deltaLabel = "vs last month",
  progressPercent,
  progressBarColor = "bg-brand",
  children,
  onClick,
}: Props) {
  return (
    <Card
      onClick={onClick}
      hoverable={!!onClick}
      className={`relative overflow-hidden transition-all duration-200 ${tint}`}
    >
      <div className="flex items-start justify-between">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wider text-stone-500">{label}</p>
          <p className="mt-2 font-display text-3xl font-extrabold tracking-tight text-ink sm:text-4xl">
            {value}
          </p>
        </div>
        <span className="grid h-10 w-10 shrink-0 place-items-center rounded-2xl bg-white/80 text-brand-dark shadow-xs backdrop-blur">
          <Icon name={icon} className="h-5 w-5" />
        </span>
      </div>

      {/* Delta or Progress Bar */}
      {typeof progressPercent === "number" && (
        <div className="mt-3 space-y-1">
          <div className="h-2 w-full overflow-hidden rounded-full bg-black/5">
            <div
              className={`h-full rounded-full transition-all duration-500 ${progressBarColor}`}
              style={{ width: `${Math.min(Math.max(progressPercent, 0), 100)}%` }}
            />
          </div>
          <div className="flex justify-between text-[10px] font-semibold text-stone-500">
            <span>Progress</span>
            <span>{progressPercent}%</span>
          </div>
        </div>
      )}

      {delta !== undefined && delta !== null && (
        <div className="mt-2.5 flex items-center gap-1.5 text-xs">
          <span
            className={`inline-flex items-center gap-0.5 rounded-md px-1.5 py-0.5 font-bold ${
              delta >= 0
                ? "bg-emerald-100 text-emerald-800"
                : "bg-red-100 text-red-800"
            }`}
          >
            {delta >= 0 ? "▲" : "▼"} {Math.abs(delta).toFixed(1)}%
          </span>
          <span className="text-stone-500">{deltaLabel}</span>
        </div>
      )}

      {/* Subtext and Extra Children */}
      <div className="mt-3 flex items-end justify-between border-t border-line/40 pt-2 text-xs text-stone-600">
        <div>{sub}</div>
        {children}
      </div>
    </Card>
  );
}
