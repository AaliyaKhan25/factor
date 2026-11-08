"use client";

import { useState } from "react";
import Link from "next/link";
import Icon from "@/components/ui/Icon";
import { rupees } from "@/lib/format";

interface Props {
  salesMonthPaise: number;
  salesPrevMonthPaise: number;
  ordersToFulfil: number;
  readyToShip: number;
  inProgress: number;
  unpaidCount: number;
  unpaidPaise: number;
  messagesOpen: number;
  agentHandled: number;
  daily: { date: string; total_paise: number }[];
}

export default function ProgressTrackers({
  salesMonthPaise,
  salesPrevMonthPaise,
  ordersToFulfil,
  readyToShip,
  inProgress,
  unpaidCount,
  unpaidPaise,
  messagesOpen,
  agentHandled,
  daily,
}: Props) {
  // Configurable monthly sales target (default ₹50,000 or 1.25x last month)
  const defaultTarget = Math.max(salesPrevMonthPaise > 0 ? Math.round(salesPrevMonthPaise * 1.25) : 5000000, 5000000);
  const [monthlyTarget, setMonthlyTarget] = useState(defaultTarget);
  const [isEditingTarget, setIsEditingTarget] = useState(false);

  // Target calculation
  const targetPercent = Math.min(Math.round((salesMonthPaise / monthlyTarget) * 100), 100);
  const remainingPaise = Math.max(monthlyTarget - salesMonthPaise, 0);

  // Projected run rate based on day of month
  const now = new Date();
  const dayOfMonth = now.getDate();
  const daysInMonth = new Date(now.getFullYear(), now.getMonth() + 1, 0).getDate();
  const projectedPaise = Math.round((salesMonthPaise / Math.max(dayOfMonth, 1)) * daysInMonth);

  // Fulfillment pipeline
  const totalActiveOrders = Math.max(ordersToFulfil, 1);
  const readyPercent = Math.round((readyToShip / totalActiveOrders) * 100);
  const inProgressPercent = Math.round((inProgress / totalActiveOrders) * 100);

  // Payment collection
  const totalRevenuePaise = salesMonthPaise + unpaidPaise;
  const collectedPercent = totalRevenuePaise > 0 ? Math.round((salesMonthPaise / totalRevenuePaise) * 100) : 100;

  // AI automation rate
  const totalConvs = messagesOpen + agentHandled;
  const aiAutomationPercent = totalConvs > 0 ? Math.round((agentHandled / totalConvs) * 100) : 100;

  // Weekly 4-week breakdown
  const weeks = [
    { label: "Week 1 (1–7d)", total: daily.slice(0, 7).reduce((acc, c) => acc + c.total_paise, 0) },
    { label: "Week 2 (8–14d)", total: daily.slice(7, 14).reduce((acc, c) => acc + c.total_paise, 0) },
    { label: "Week 3 (15–21d)", total: daily.slice(14, 21).reduce((acc, c) => acc + c.total_paise, 0) },
    { label: "Week 4 (22–28d)", total: daily.slice(21, 28).reduce((acc, c) => acc + c.total_paise, 0) },
  ];
  const maxWeek = Math.max(...weeks.map((w) => w.total), 1);

  return (
    <div className="space-y-6">
      {/* 1. Monthly Revenue Milestone Progress Card */}
      <div className="rounded-2xl border border-line bg-white p-5 shadow-card transition-all hover:shadow-soft">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div className="flex items-center gap-2.5">
            <span className="grid h-8 w-8 place-items-center rounded-xl bg-brand text-brand-dark">
              <Icon name="target" className="h-4 w-4" />
            </span>
            <div>
              <h3 className="font-display text-base font-bold text-ink">Monthly Revenue Target</h3>
              <p className="text-xs text-stone-500">Day {dayOfMonth} of {daysInMonth} · Run-rate pace</p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            {isEditingTarget ? (
              <div className="flex items-center gap-1.5">
                <span className="text-xs font-semibold text-stone-500">Target ₹</span>
                <input
                  type="number"
                  defaultValue={monthlyTarget / 100}
                  onBlur={(e) => {
                    const val = Number(e.target.value);
                    if (val > 0) setMonthlyTarget(val * 100);
                    setIsEditingTarget(false);
                  }}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") {
                      const val = Number((e.target as HTMLInputElement).value);
                      if (val > 0) setMonthlyTarget(val * 100);
                      setIsEditingTarget(false);
                    }
                  }}
                  autoFocus
                  className="w-24 rounded-lg border border-brand-dark/40 px-2 py-0.5 text-xs font-bold"
                />
              </div>
            ) : (
              <button
                onClick={() => setIsEditingTarget(true)}
                className="inline-flex items-center gap-1 rounded-lg bg-cream px-2.5 py-1 text-xs font-semibold text-stone-600 hover:bg-stone-200"
                title="Change Target Goal"
              >
                <span>Goal: {rupees(monthlyTarget)}</span>
                <Icon name="gear" className="h-3 w-3 text-stone-400" />
              </button>
            )}
            <span className="rounded-full bg-brand-soft px-2.5 py-0.5 text-xs font-bold text-brand-dark">
              {targetPercent}% Achieved
            </span>
          </div>
        </div>

        {/* Progress Bar Container */}
        <div className="mt-4 space-y-2">
          <div className="relative h-4 w-full overflow-hidden rounded-full bg-cream-dark/80 p-0.5">
            <div
              className="h-full rounded-full bg-brand transition-all duration-700 ease-out"
              style={{ width: `${targetPercent}%` }}
            />
          </div>

          <div className="flex flex-wrap items-center justify-between text-xs font-medium text-stone-600">
            <span>
              Achieved: <b className="font-bold text-ink">{rupees(salesMonthPaise)}</b>
            </span>
            <span>
              Remaining: <b className="font-bold text-ink">{rupees(remainingPaise)}</b>
            </span>
          </div>
        </div>

        {/* Projected Pace Callout */}
        <div className="mt-4 grid grid-cols-1 gap-2 rounded-xl bg-cream/50 p-3 sm:grid-cols-2">
          <div className="flex items-center gap-2">
            <span className="grid h-6 w-6 place-items-center rounded-lg bg-white text-stone-600">
              <Icon name="trending" className="h-3.5 w-3.5" />
            </span>
            <div className="text-xs">
              <span className="text-stone-500">Estimated Month-End: </span>
              <span className="font-bold text-ink">{rupees(projectedPaise)}</span>
            </div>
          </div>
          <div className="flex items-center gap-2 sm:justify-end">
            <span className="text-xs text-stone-500">
              {projectedPaise >= monthlyTarget ? (
                <span className="font-semibold text-emerald-700">✓ On track to exceed goal by {rupees(projectedPaise - monthlyTarget)}</span>
              ) : (
                <span className="font-semibold text-amber-700">⚠ Needs {rupees(Math.round((monthlyTarget - salesMonthPaise) / Math.max(daysInMonth - dayOfMonth, 1)))}/day to hit target</span>
              )}
            </span>
          </div>
        </div>
      </div>

      {/* 2. Order Fulfillment & Pipeline Multi-Segment Progress Bar */}
      <div className="rounded-2xl border border-line bg-white p-5 shadow-card transition-all hover:shadow-soft">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <span className="grid h-8 w-8 place-items-center rounded-xl bg-brand-soft text-brand-dark">
              <Icon name="truck" className="h-4 w-4" />
            </span>
            <div>
              <h3 className="font-display text-base font-bold text-ink">Order Fulfillment Pipeline</h3>
              <p className="text-xs text-stone-500">{ordersToFulfil} active orders in progress</p>
            </div>
          </div>
          <Link
            href="/orders"
            className="flex items-center gap-1 text-xs font-bold text-brand-dark hover:underline"
          >
            Manage orders <Icon name="arrow" className="h-3 w-3" />
          </Link>
        </div>

        {/* Stacked Progress Bar */}
        <div className="mt-4 space-y-2">
          <div className="flex h-3.5 w-full overflow-hidden rounded-full bg-stone-100">
            {readyToShip > 0 && (
              <div
                title={`${readyToShip} Ready to ship`}
                className="h-full bg-brand transition-all duration-500"
                style={{ width: `${readyPercent}%` }}
              />
            )}
            {inProgress > 0 && (
              <div
                title={`${inProgress} In progress / packing`}
                className="h-full bg-amber-400 transition-all duration-500"
                style={{ width: `${inProgressPercent}%` }}
              />
            )}
            {ordersToFulfil === 0 && (
              <div className="h-full w-full bg-emerald-200" title="All caught up" />
            )}
          </div>

          {/* Bar Legend */}
          <div className="flex flex-wrap items-center gap-4 text-xs">
            <div className="flex items-center gap-1.5">
              <span className="h-2.5 w-2.5 rounded-full bg-brand" />
              <span className="font-medium text-stone-700">Ready to Ship: <b>{readyToShip}</b></span>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="h-2.5 w-2.5 rounded-full bg-amber-400" />
              <span className="font-medium text-stone-700">In Production/Progress: <b>{inProgress}</b></span>
            </div>
            {ordersToFulfil === 0 && (
              <div className="flex items-center gap-1.5 text-emerald-700 font-semibold">
                <Icon name="check" className="h-3.5 w-3.5" /> All orders delivered or packed!
              </div>
            )}
          </div>
        </div>
      </div>

      {/* 3. Side-by-side Progress Metrics: Cashflow & AI Support */}
      <div className="grid gap-4 sm:grid-cols-2">
        {/* Cashflow Realization Progress */}
        <div className="rounded-2xl border border-line bg-white p-4 shadow-card">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span className="grid h-7 w-7 place-items-center rounded-lg bg-emerald-100 text-emerald-800">
                <Icon name="wallet" className="h-4 w-4" />
              </span>
              <p className="text-xs font-bold text-ink">Cash Realization</p>
            </div>
            <span className="text-xs font-bold text-emerald-700">{collectedPercent}% Collected</span>
          </div>

          <div className="mt-3 h-2.5 w-full overflow-hidden rounded-full bg-stone-100">
            <div
              className="h-full rounded-full bg-emerald-500 transition-all duration-500"
              style={{ width: `${collectedPercent}%` }}
            />
          </div>

          <div className="mt-2.5 flex items-center justify-between text-[11px] text-stone-500">
            <span>Collected: <b>{rupees(salesMonthPaise)}</b></span>
            <span>Unpaid: <b className="text-red-700">{rupees(unpaidPaise)}</b> ({unpaidCount})</span>
          </div>
        </div>

        {/* AI Support Automation Rate */}
        <div className="rounded-2xl border border-line bg-white p-4 shadow-card">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span className="grid h-7 w-7 place-items-center rounded-lg bg-brand text-brand-dark">
                <Icon name="spark" className="h-4 w-4" />
              </span>
              <p className="text-xs font-bold text-ink">AI Assistant Handled</p>
            </div>
            <span className="text-xs font-bold text-brand-dark">{aiAutomationPercent}% Autopilot</span>
          </div>

          <div className="mt-3 h-2.5 w-full overflow-hidden rounded-full bg-stone-100">
            <div
              className="h-full rounded-full bg-brand transition-all duration-500"
              style={{ width: `${aiAutomationPercent}%` }}
            />
          </div>

          <div className="mt-2.5 flex items-center justify-between text-[11px] text-stone-500">
            <span>AI Handled: <b>{agentHandled} chats</b></span>
            <span>Waiting on you: <b className="text-amber-800">{messagesOpen}</b></span>
          </div>
        </div>
      </div>

      {/* 4. Weekly 4-Week Momentum Comparison Horizontal Bar Chart */}
      <div className="rounded-2xl border border-line bg-white p-5 shadow-card transition-all hover:shadow-soft">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="font-display text-base font-bold text-ink">4-Week Sales Momentum</h3>
            <p className="text-xs text-stone-500">Weekly revenue pacing across the last 28 days</p>
          </div>
          <span className="text-[11px] font-bold text-stone-400 uppercase tracking-wider">Comparative</span>
        </div>

        <div className="mt-4 space-y-3">
          {weeks.map((w, idx) => {
            const barWidth = maxWeek > 0 ? Math.max((w.total / maxWeek) * 100, w.total > 0 ? 6 : 2) : 2;
            const isCurrentWeek = idx === 3;

            return (
              <div key={w.label} className="space-y-1">
                <div className="flex items-center justify-between text-xs">
                  <span className={`font-medium ${isCurrentWeek ? "font-bold text-ink" : "text-stone-600"}`}>
                    {w.label} {isCurrentWeek && <span className="ml-1 rounded-md bg-brand-soft px-1.5 py-0.2 text-[9px] font-bold text-brand-dark">Current</span>}
                  </span>
                  <span className="font-mono text-xs font-semibold text-ink">{rupees(w.total)}</span>
                </div>
                <div className="h-3 w-full overflow-hidden rounded-full bg-stone-100">
                  <div
                    className={`h-full rounded-full transition-all duration-500 ${
                      isCurrentWeek ? "bg-brand" : "bg-brand-dark/70"
                    }`}
                    style={{ width: `${barWidth}%` }}
                  />
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
