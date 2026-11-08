"use client";
import Link from "next/link";
import { api, Dashboard } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { rupees } from "@/lib/format";
import { usePolling } from "@/hooks/usePolling";
import Card from "@/components/ui/Card";
import Icon from "@/components/ui/Icon";

function greeting() {
  const h = new Date().getHours();
  return h < 12 ? "Good morning" : h < 17 ? "Good afternoon" : "Good evening";
}

function Kpi({ label, value, sub, icon, tint, children }: { label: string; value: string; sub: React.ReactNode; icon: string; tint: string; children?: React.ReactNode }) {
  return (
    <Card className={tint}>
      <div className="flex items-start justify-between">
        <p className="text-sm text-stone-600">{label}</p>
        <span className="grid h-9 w-9 place-items-center rounded-xl bg-white/70 text-brand-dark"><Icon name={icon} className="h-5 w-5" /></span>
      </div>
      <p className="mt-4 font-serif text-4xl font-bold tracking-tight">{value}</p>
      <div className="mt-2 flex items-end justify-between text-xs text-stone-500">
        <div>{sub}</div>
        {children}
      </div>
    </Card>
  );
}

export default function DashboardPage() {
  const { user, business } = useAuth();
  const { data: d, error, loading } = usePolling(() => api<Dashboard>("/dashboard"), 8000);
  const today = new Date().toLocaleDateString("en-IN", { weekday: "long", day: "numeric", month: "long", year: "numeric" });

  if (error && !d) {
    return <p className="rounded-xl bg-white p-4 text-stone-600">{error.includes("Missing permission") ? "Ask the owner for access to the overview." : error}</p>;
  }
  if (loading || !d) return <p className="text-stone-500">Loading…</p>;

  const delta = d.sales_prev_month_paise > 0 ? ((d.sales_month_paise - d.sales_prev_month_paise) / d.sales_prev_month_paise) * 100 : null;
  const max = Math.max(...d.daily.map((x) => x.total_paise), 1);
  const empty = d.daily.every((x) => x.total_paise === 0);

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="text-[11px] font-bold uppercase tracking-widest text-stone-500"><span className="mr-2 inline-block h-2 w-2 rounded-full bg-brand-dark" />{today}</p>
          <h1 className="mt-2 font-serif text-4xl font-bold">{greeting()}, {user?.name.split(" ")[0]}</h1>
          <p className="mt-1 text-stone-600">
            {d.messages_open > 0 ? `${d.messages_open} ${d.messages_open === 1 ? "chat needs" : "chats need"} you.` : "No chats are waiting on you."}{" "}
            {d.agent_handled > 0 ? `The agent is handling ${d.agent_handled}.` : ""}
          </p>
        </div>
        <Link href="/orders/new" className="inline-flex min-h-12 items-center gap-2 rounded-2xl bg-brand px-5 font-bold hover:bg-brand-hover">
          <Icon name="plus" className="h-5 w-5" /> Create an order
        </Link>
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        <Kpi label="Sales this month" value={rupees(d.sales_month_paise)} icon="spark" tint="!bg-brand-soft"
          sub={delta === null ? "No sales last month yet" : <span className={delta >= 0 ? "font-bold text-emerald-700" : "font-bold text-red-700"}>{delta >= 0 ? "▲" : "▼"} {Math.abs(delta).toFixed(1)}% <span className="font-normal text-stone-500">vs last month</span></span>}>
          <div className="flex h-10 items-end gap-1" aria-hidden="true">
            {d.daily.slice(-12).map((x) => <span key={x.date} className="w-1.5 rounded-sm bg-brand-dark/70" style={{ height: `${Math.max((x.total_paise / max) * 100, 6)}%` }} />)}
          </div>
        </Kpi>
        <Kpi label="Orders to fulfil" value={String(d.orders_to_fulfil)} icon="box" tint=""
          sub={<><b className="text-ink">{d.ready_to_ship}</b> ready to ship · <b className="text-ink">{d.in_progress}</b> in progress</>} />
        <Kpi label="Awaiting payment" value={rupees(d.unpaid_paise)} icon="wallet" tint=""
          sub={<><b className="text-ink">{d.unpaid_count}</b> {d.unpaid_count === 1 ? "order" : "orders"} unpaid</>} />
        <Kpi label="Customer messages" value={String(d.messages_open).padStart(2, "0")} icon="inbox" tint=""
          sub={<>{d.agent_handled} handled by the agent</>}>
          <Link href="/inbox" className="flex items-center gap-1 font-semibold text-brand-dark">Go to inbox <Icon name="arrow" className="h-3.5 w-3.5" /></Link>
        </Kpi>
      </div>

      <div className="grid gap-4 lg:grid-cols-[1.4fr_1fr]">
        <Card>
          <h2 className="font-serif text-xl font-bold">Sales at a glance</h2>
          <p className="text-sm text-stone-500">Order value per day, last 28 days.</p>
          {empty ? (
            <p className="mt-6 rounded-xl bg-cream p-6 text-center text-sm text-stone-500">No orders yet. Orders you create or the agent books will show here.</p>
          ) : (
            <div className="mt-6 flex h-44 items-end gap-1">
              {d.daily.map((x) => (
                <div key={x.date} title={`${x.date}: ${rupees(x.total_paise)}`} className="flex-1 rounded-t bg-brand" style={{ height: `${Math.max((x.total_paise / max) * 100, 2)}%` }} />
              ))}
            </div>
          )}
        </Card>
        <Card>
          <div className="flex items-center justify-between">
            <h2 className="font-serif text-xl font-bold">A few things to take care of</h2>
            {d.todo.length ? <span className="rounded-full bg-amber-100 px-2 py-0.5 text-xs font-bold text-amber-800">{d.todo.length}</span> : null}
          </div>
          <ul className="mt-3 divide-y divide-line">
            {d.todo.map((t) => (
              <li key={t.kind}>
                <Link href={t.href} className="flex items-center gap-3 py-3">
                  <span className="grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-brand-soft text-brand-dark">
                    <Icon name={t.kind === "inbox" ? "inbox" : t.kind === "payments" ? "wallet" : t.kind === "ship" ? "truck" : "box"} />
                  </span>
                  <span className="min-w-0 flex-1"><span className="block text-sm font-bold">{t.title}</span><span className="block truncate text-xs text-stone-500">{t.detail}</span></span>
                  <Icon name="arrow" className="h-4 w-4 text-stone-400" />
                </Link>
              </li>
            ))}
          </ul>
          {d.todo.length === 0 ? <p className="mt-4 rounded-xl bg-cream p-4 text-sm text-stone-500">You are all caught up at {business?.name}.</p> : null}
        </Card>
      </div>
    </div>
  );
}
