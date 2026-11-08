"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import { api, Dashboard } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { rupees } from "@/lib/format";
import { usePolling } from "@/hooks/usePolling";
import Card from "@/components/ui/Card";
import Icon from "@/components/ui/Icon";
import KpiCard from "@/components/dashboard/KpiCard";
import InteractiveSalesChart from "@/components/dashboard/InteractiveSalesChart";
import ProgressTrackers from "@/components/dashboard/ProgressTrackers";
import ActionCenter from "@/components/dashboard/ActionCenter";
import VoiceOrderModal from "@/components/voice/VoiceOrderModal";

function greeting() {
  const h = new Date().getHours();
  return h < 12 ? "Good morning" : h < 17 ? "Good afternoon" : "Good evening";
}

// Generates rich sample data for previewing active statistics
function generateSimulatedDashboard(): Dashboard {
  const today = new Date();
  const daily = [];
  const baseSales = [3200, 4800, 1500, 6200, 8900, 12400, 7500, 2100, 5400, 9800, 4100, 8200, 14500, 11200];

  for (let i = 27; i >= 0; i--) {
    const d = new Date(today);
    d.setDate(today.getDate() - i);
    const dateStr = d.toISOString().split("T")[0];
    const isWeekend = d.getDay() === 0 || d.getDay() === 6;
    const base = baseSales[i % baseSales.length];
    const multiplier = isWeekend ? 1.6 : 1.0;
    const paise = Math.round(base * multiplier * 100);
    daily.push({ date: dateStr, total_paise: paise });
  }

  const thisMonthPaise = daily.slice(-14).reduce((a, b) => a + b.total_paise, 0);
  const prevMonthPaise = Math.round(thisMonthPaise * 0.82);

  return {
    sales_month_paise: thisMonthPaise,
    sales_prev_month_paise: prevMonthPaise,
    orders_to_fulfil: 7,
    ready_to_ship: 4,
    in_progress: 3,
    unpaid_count: 2,
    unpaid_paise: 840000,
    messages_open: 3,
    agent_handled: 18,
    daily,
    todo: [
      { kind: "inbox", title: "Reply to 3 customers", detail: "Meera Shah, Ananya Rao, Kavya Nair are waiting", href: "/inbox" },
      { kind: "ship", title: "Ship 4 packed orders", detail: "FX-2481, FX-2479 ready for pickup", href: "/orders" },
      { kind: "payments", title: "2 orders are unpaid", detail: "₹8,400 to verify and collect", href: "/orders" },
    ],
    customers: 24,
  };
}

export default function DashboardPage() {
  const { user, business } = useAuth();
  const { data: realData, error, loading, reload } = usePolling(() => api<Dashboard>("/dashboard"), 8000);
  const [useSimulation, setUseSimulation] = useState(false);
  const [selectedDayFocus, setSelectedDayFocus] = useState<{ date: string; total_paise: number } | null>(null);
  const [voiceModalOpen, setVoiceModalOpen] = useState(false);

  const today = new Date().toLocaleDateString("en-IN", {
    weekday: "long",
    day: "numeric",
    month: "long",
    year: "numeric",
  });

  // Decide whether to show real data or simulated preview
  const isRealEmpty = realData?.daily?.every((x) => x.total_paise === 0) ?? true;
  const simulatedData = useMemo(() => generateSimulatedDashboard(), []);
  const d = useSimulation || (isRealEmpty && useSimulation) ? simulatedData : realData;

  if (error && !realData) {
    return (
      <div className="mx-auto max-w-4xl p-6">
        <div className="rounded-2xl border border-red-200 bg-red-50/70 p-6 text-center text-ink">
          <Icon name="info" className="mx-auto h-8 w-8 text-red-600 mb-2" />
          <h2 className="font-display text-lg font-bold">Unable to load dashboard</h2>
          <p className="mt-1 text-sm text-stone-600">
            {error.includes("Missing permission") ? "Ask the owner for access to the overview." : error}
          </p>
        </div>
      </div>
    );
  }

  if (loading || !d) {
    return (
      <div className="mx-auto max-w-6xl space-y-6 animate-pulse">
        <div className="h-14 w-64 rounded-2xl bg-stone-200/60" />
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="h-36 rounded-2xl bg-stone-200/60" />
          ))}
        </div>
        <div className="h-72 rounded-2xl bg-stone-200/60" />
      </div>
    );
  }

  // Delta calculations
  const delta =
    d.sales_prev_month_paise > 0
      ? ((d.sales_month_paise - d.sales_prev_month_paise) / d.sales_prev_month_paise) * 100
      : null;

  const sparkMax = Math.max(...d.daily.map((x) => x.total_paise), 1);
  const totalActive = Math.max(d.orders_to_fulfil, 1);
  const fulfillmentRate = Math.round((d.ready_to_ship / totalActive) * 100);
  const totalMoney = d.sales_month_paise + d.unpaid_paise;
  const cashCollectionRate = totalMoney > 0 ? Math.round((d.sales_month_paise / totalMoney) * 100) : 100;

  return (
    <div className="mx-auto max-w-6xl space-y-7 pb-12">
      {/* Top Banner / Live Indicator & Header */}
      <div className="flex flex-wrap items-end justify-between gap-4 border-b border-line/60 pb-6">
        <div>
          <div className="flex items-center gap-2">
            <span className="flex h-2 w-2 rounded-full bg-brand-dark animate-pulse" />
            <p className="text-[11px] font-bold uppercase tracking-wider text-stone-600">
              {today} · Operations Hub
            </p>
            {useSimulation && (
              <span className="rounded-md bg-amber-100 px-2 py-0.5 text-[10px] font-bold text-amber-900">
                Interactive Demo Mode
              </span>
            )}
          </div>
          <h1 className="mt-1 font-display text-3xl font-extrabold tracking-tight text-ink sm:text-4xl">
            {greeting()}, {user?.name.split(" ")[0]}
          </h1>
          <p className="mt-1 text-sm text-stone-600">
            {d.messages_open > 0 ? (
              <span className="font-semibold text-ink">
                {d.messages_open} {d.messages_open === 1 ? "customer chat needs" : "customer chats need"} your reply.
              </span>
            ) : (
              "No chats are waiting on you."
            )}{" "}
            {d.agent_handled > 0 ? (
              <span className="text-brand-dark font-medium">The AI assistant resolved {d.agent_handled} conversations.</span>
            ) : null}
          </p>
        </div>

        {/* Action Controls */}
        <div className="flex flex-wrap items-center gap-2.5">
          {/* Data Switcher: Real vs Simulation preview */}
          <button
            onClick={() => setUseSimulation(!useSimulation)}
            className={`inline-flex items-center gap-1.5 rounded-xl border px-3 py-2 text-xs font-semibold transition-all ${
              useSimulation
                ? "border-amber-300 bg-amber-50 text-amber-900 shadow-sm"
                : "border-line bg-white text-stone-600 hover:bg-stone-50"
            }`}
            title="Toggle interactive simulated numbers"
          >
            <Icon name="spark" className="h-3.5 w-3.5" />
            <span>{useSimulation ? "View Live Data" : "Preview With Data"}</span>
          </button>

          <button
            onClick={() => reload()}
            className="grid h-11 w-11 place-items-center rounded-xl border border-line bg-white text-stone-600 shadow-sm transition-transform hover:bg-stone-50 active:scale-95"
            title="Refresh statistics"
          >
            <Icon name="refresh" className="h-4 w-4" />
          </button>

          <button
            onClick={() => setVoiceModalOpen(true)}
            className="inline-flex min-h-11 items-center gap-2 rounded-xl border border-brand bg-white px-4 text-xs font-bold text-ink shadow-sm transition-all hover:bg-brand-soft hover:border-brand-dark/40 active:scale-95"
            title="Voice order powered by Gnani.ai"
          >
            <span className="grid h-5 w-5 place-items-center rounded-md bg-brand text-brand-dark">
              <Icon name="mic" className="h-3 w-3" />
            </span>
            <span>Voice Order</span>
          </button>

          <Link
            href="/orders/new"
            className="inline-flex min-h-11 items-center gap-2 rounded-xl bg-brand px-5 text-sm font-bold text-ink shadow-sm transition-all hover:bg-brand-hover hover:shadow-glow active:scale-95"
          >
            <Icon name="plus" className="h-4 w-4" /> Create order
          </Link>
        </div>
      </div>

      {/* 4 Interactive Statistical KPI Cards */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {/* KPI 1: Monthly Sales */}
        <KpiCard
          label="Sales this month"
          value={rupees(d.sales_month_paise)}
          icon="spark"
          tint="!bg-brand-soft/80 border-brand/50 shadow-soft"
          delta={delta}
          deltaLabel="vs last month"
          sub={
            <div className="flex items-center gap-2">
              <span className="font-semibold text-ink">
                {rupees(Math.round(d.sales_month_paise / Math.max(new Date().getDate(), 1)))}/day
              </span>
              <span className="text-stone-400">avg</span>
            </div>
          }
        >
          {/* Mini Sparkline Bar Visualization */}
          <div className="flex h-10 items-end gap-1" aria-hidden="true">
            {d.daily.slice(-10).map((x) => (
              <span
                key={x.date}
                className="w-1.5 rounded-sm bg-brand-dark/70 transition-all hover:bg-brand-dark hover:scale-110"
                style={{ height: `${Math.max((x.total_paise / sparkMax) * 100, 10)}%` }}
                title={`${x.date}: ${rupees(x.total_paise)}`}
              />
            ))}
          </div>
        </KpiCard>

        {/* KPI 2: Orders to Fulfill */}
        <KpiCard
          label="Orders to fulfil"
          value={String(d.orders_to_fulfil)}
          icon="box"
          sub={
            <span>
              <b className="font-bold text-ink">{d.ready_to_ship}</b> ready to ship ·{" "}
              <b className="font-bold text-ink">{d.in_progress}</b> in progress
            </span>
          }
          progressPercent={fulfillmentRate}
          progressBarColor="bg-brand"
        >
          <Link
            href="/orders"
            className="flex items-center gap-1 font-bold text-xs text-brand-dark hover:underline"
          >
            View <Icon name="arrow" className="h-3 w-3" />
          </Link>
        </KpiCard>

        {/* KPI 3: Cashflow / Unpaid */}
        <KpiCard
          label="Awaiting payment"
          value={rupees(d.unpaid_paise)}
          icon="wallet"
          sub={
            <span>
              <b className="font-bold text-ink">{d.unpaid_count}</b>{" "}
              {d.unpaid_count === 1 ? "order" : "orders"} unpaid
            </span>
          }
          progressPercent={cashCollectionRate}
          progressBarColor="bg-emerald-500"
        >
          <Link
            href="/orders"
            className="flex items-center gap-1 font-bold text-xs text-brand-dark hover:underline"
          >
            Collect <Icon name="arrow" className="h-3 w-3" />
          </Link>
        </KpiCard>

        {/* KPI 4: Customer Inquiries & AI */}
        <KpiCard
          label="Customer messages"
          value={String(d.messages_open).padStart(2, "0")}
          icon="inbox"
          sub={
            <span className="text-brand-dark font-medium">
              <b>{d.agent_handled}</b> resolved by AI
            </span>
          }
        >
          <Link
            href="/inbox"
            className="flex items-center gap-1 font-bold text-xs text-brand-dark hover:underline"
          >
            Go to inbox <Icon name="arrow" className="h-3.5 w-3.5" />
          </Link>
        </KpiCard>
      </div>

      {/* Main Statistical Section: Interactive Sales Bar Graph & Action Center */}
      <div className="grid gap-6 lg:grid-cols-[1.55fr_1fr]">
        {/* Interactive Bar Graph Section */}
        <Card className="shadow-card">
          <InteractiveSalesChart
            daily={d.daily}
            onSelectDay={(day) => setSelectedDayFocus(day)}
          />
        </Card>

        {/* Action Center / High Priority Tasks */}
        <ActionCenter items={d.todo} businessName={business?.name} />
      </div>

      {/* Comprehensive Progress Bar Graphs & Goal Metrics */}
      <div className="space-y-4">
        <div className="flex items-center justify-between border-b border-line/60 pb-2">
          <div>
            <h2 className="font-display text-xl font-bold text-ink">Operational Progress & Benchmarks</h2>
            <p className="text-xs text-stone-500">Live progress bars, fulfillment rates, and revenue pacing</p>
          </div>
          <span className="rounded-full bg-brand-soft px-3 py-1 text-xs font-bold text-brand-dark">
            Real-time Metrics
          </span>
        </div>

        <ProgressTrackers
          salesMonthPaise={d.sales_month_paise}
          salesPrevMonthPaise={d.sales_prev_month_paise}
          ordersToFulfil={d.orders_to_fulfil}
          readyToShip={d.ready_to_ship}
          inProgress={d.in_progress}
          unpaidCount={d.unpaid_count}
          unpaidPaise={d.unpaid_paise}
          messagesOpen={d.messages_open}
          agentHandled={d.agent_handled}
          daily={d.daily}
        />
      </div>

      {voiceModalOpen && (
        <VoiceOrderModal
          onClose={() => setVoiceModalOpen(false)}
          onOrderCreated={() => reload()}
        />
      )}
    </div>
  );
}
