"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import { api, OrderSummary } from "@/lib/api";
import { rupees, timeAgo } from "@/lib/format";
import { usePolling } from "@/hooks/usePolling";
import Badge from "@/components/ui/Badge";
import Card from "@/components/ui/Card";
import ChannelBadge from "@/components/ui/ChannelBadge";
import StatusBadge from "@/components/orders/StatusBadge";

const FILTERS = ["all", "new", "confirmed", "packed", "shipped", "delivered", "cancelled"];

export default function OrdersPage() {
  const [status, setStatus] = useState("all");
  const { data, error, loading } = usePolling(() => api<OrderSummary[]>("/orders"), 6000);

  useEffect(() => {
    const s = new URLSearchParams(window.location.search).get("status");
    if (s && FILTERS.includes(s)) setStatus(s);
  }, []);

  if (error && !data) return <p className="rounded-xl bg-white p-4 text-stone-600">{error.includes("Missing permission") ? "Ask the owner for access to orders." : error}</p>;
  const rows = (data ?? []).filter((o) => status === "all" || o.status === status);
  const count = (s: string) => (data ?? []).filter((o) => s === "all" || o.status === s).length;

  return (
    <div className="mx-auto max-w-5xl space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="font-serif text-3xl font-bold">Orders</h1>
        <Link href="/orders/new" className="inline-flex min-h-10 items-center rounded-xl bg-brand px-4 text-sm font-bold hover:bg-brand-hover">New order</Link>
      </div>
      <div className="flex gap-2 overflow-x-auto pb-1">
        {FILTERS.map((f) => (
          <button key={f} onClick={() => setStatus(f)} className={`shrink-0 rounded-full border px-3.5 py-1.5 text-sm font-semibold capitalize ${status === f ? "border-brand-dark bg-brand-soft text-brand-dark" : "border-line bg-white text-stone-600"}`}>
            {f} <span className="text-xs opacity-70">{count(f)}</span>
          </button>
        ))}
      </div>
      <Card className="!p-0">
        {loading ? <p className="p-6 text-stone-500">Loading…</p> : rows.length === 0 ? (
          <p className="p-8 text-center text-stone-500">{data?.length ? "No orders with this status." : "No orders yet. The agent books them from chats, or you can create one."}</p>
        ) : (
          <ul className="divide-y divide-line">
            {rows.map((o) => (
              <li key={o.id}>
                <Link href={`/orders/${o.id}`} className="flex items-center gap-3 p-4 hover:bg-stone-50">
                  <div className="min-w-0 flex-1">
                    <p className="flex items-center gap-2 font-bold">{o.code} <ChannelBadge channel={o.source} /></p>
                    <p className="truncate text-sm text-stone-600">{o.customer_name} · {timeAgo(o.created_at)}</p>
                  </div>
                  <div className="text-right">
                    <p className="font-bold">{rupees(o.total_paise)}</p>
                    <div className="mt-1 flex justify-end gap-1"><StatusBadge status={o.status} /><Badge tone={o.payment_status === "paid" ? "green" : "amber"}>{o.payment_status}</Badge></div>
                  </div>
                </Link>
              </li>
            ))}
          </ul>
        )}
      </Card>
    </div>
  );
}
