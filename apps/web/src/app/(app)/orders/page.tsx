"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { api, OrderSummary } from "@/lib/api";
import { rupees, timeAgo } from "@/lib/format";
import { usePolling } from "@/hooks/usePolling";
import Badge from "@/components/ui/Badge";
import Card from "@/components/ui/Card";
import ChannelBadge from "@/components/ui/ChannelBadge";
import StatusBadge from "@/components/orders/StatusBadge";
import Icon from "@/components/ui/Icon";
import VoiceOrderModal from "@/components/voice/VoiceOrderModal";

const FILTERS = ["all", "new", "confirmed", "packed", "shipped", "delivered", "cancelled"];

export default function OrdersPage() {
  const [status, setStatus] = useState("all");
  const [search, setSearch] = useState("");
  const [voiceModalOpen, setVoiceModalOpen] = useState(false);
  const { data, error, loading, reload } = usePolling(() => api<OrderSummary[]>("/orders"), 6000);

  useEffect(() => {
    const s = new URLSearchParams(window.location.search).get("status");
    if (s && FILTERS.includes(s)) setStatus(s);
  }, []);

  const allOrders = data ?? [];

  // Filtered rows
  const rows = useMemo(() => {
    return allOrders.filter((o) => {
      const matchesStatus = status === "all" || o.status === status;
      const q = search.toLowerCase().trim();
      const matchesSearch =
        !q ||
        o.code.toLowerCase().includes(q) ||
        o.customer_name.toLowerCase().includes(q) ||
        o.source.toLowerCase().includes(q);
      return matchesStatus && matchesSearch;
    });
  }, [allOrders, status, search]);

  const count = (s: string) => allOrders.filter((o) => s === "all" || o.status === s).length;

  // Statistical calculations
  const totalValuePaise = rows.reduce((acc, o) => acc + o.total_paise, 0);
  const paidCount = rows.filter((o) => o.payment_status === "paid").length;
  const paidPercent = rows.length > 0 ? Math.round((paidCount / rows.length) * 100) : 0;
  const fulfilledCount = rows.filter((o) => o.status === "shipped" || o.status === "delivered").length;
  const fulfilledPercent = rows.length > 0 ? Math.round((fulfilledCount / rows.length) * 100) : 0;

  if (error && !data) {
    return (
      <div className="mx-auto max-w-5xl rounded-2xl bg-white p-6 text-stone-600 shadow-sm border border-line">
        <Icon name="info" className="h-6 w-6 text-red-600 mb-2" />
        <p className="font-semibold">{error.includes("Missing permission") ? "Ask the owner for access to orders." : error}</p>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-5xl space-y-6">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="font-display text-3xl font-extrabold tracking-tight text-ink">Orders</h1>
          <p className="mt-0.5 text-xs text-stone-500">Track and fulfill orders booked from chats</p>
        </div>
        <div className="flex items-center gap-2">
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
            <Icon name="plus" className="h-4 w-4" /> New order
          </Link>
        </div>
      </div>

      {/* Statistical Overview Bar */}
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <Card className="!p-3.5">
          <p className="text-[10px] font-bold uppercase tracking-wider text-stone-500">Filtered Orders</p>
          <p className="mt-1 font-display text-xl font-bold text-ink">{rows.length}</p>
          <p className="text-[11px] text-stone-400">Total in view</p>
        </Card>
        <Card className="!p-3.5">
          <p className="text-[10px] font-bold uppercase tracking-wider text-stone-500">Total Value</p>
          <p className="mt-1 font-display text-xl font-bold text-ink">{rupees(totalValuePaise)}</p>
          <p className="text-[11px] text-stone-400">Sum of order value</p>
        </Card>
        <Card className="!p-3.5">
          <div className="flex items-center justify-between">
            <p className="text-[10px] font-bold uppercase tracking-wider text-stone-500">Payment Status</p>
            <span className="text-[11px] font-bold text-emerald-700">{paidPercent}% Paid</span>
          </div>
          <div className="mt-2.5 h-2 w-full overflow-hidden rounded-full bg-stone-100">
            <div className="h-full rounded-full bg-emerald-500 transition-all duration-500" style={{ width: `${paidPercent}%` }} />
          </div>
          <p className="mt-1.5 text-[11px] text-stone-500">{paidCount} of {rows.length} settled</p>
        </Card>
        <Card className="!p-3.5">
          <div className="flex items-center justify-between">
            <p className="text-[10px] font-bold uppercase tracking-wider text-stone-500">Dispatched Rate</p>
            <span className="text-[11px] font-bold text-brand-dark">{fulfilledPercent}% Shipped</span>
          </div>
          <div className="mt-2.5 h-2 w-full overflow-hidden rounded-full bg-stone-100">
            <div className="h-full rounded-full bg-brand transition-all duration-500" style={{ width: `${fulfilledPercent}%` }} />
          </div>
          <p className="mt-1.5 text-[11px] text-stone-500">{fulfilledCount} completed or sent</p>
        </Card>
      </div>

      {/* Search and Filters Bar */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex gap-1.5 overflow-x-auto pb-1">
          {FILTERS.map((f) => (
            <button
              key={f}
              onClick={() => setStatus(f)}
              className={`shrink-0 rounded-xl border px-3.5 py-1.5 text-xs font-semibold capitalize transition-all ${
                status === f
                  ? "border-brand-dark bg-brand-soft font-bold text-brand-dark shadow-xs"
                  : "border-line bg-white text-stone-600 hover:bg-stone-50"
              }`}
            >
              {f} <span className="ml-1 rounded-full bg-black/5 px-1.5 py-0.2 text-[10px]">{count(f)}</span>
            </button>
          ))}
        </div>

        <div className="relative min-w-[220px]">
          <input
            type="text"
            placeholder="Search orders or customer..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="h-9 w-full rounded-xl border border-line bg-white pl-8 pr-3 text-xs placeholder:text-stone-400 focus:border-brand-dark focus:outline-none"
          />
          <span className="absolute left-2.5 top-2.5 text-stone-400">
            <Icon name="spark" className="h-4 w-4" />
          </span>
          {search && (
            <button
              onClick={() => setSearch("")}
              className="absolute right-2.5 top-2.5 text-stone-400 hover:text-ink"
            >
              <Icon name="close" className="h-4 w-4" />
            </button>
          )}
        </div>
      </div>

      {/* Orders List Table Card */}
      <Card className="!p-0 overflow-hidden shadow-card">
        {loading ? (
          <div className="space-y-4 p-6">
            {[1, 2, 3].map((i) => (
              <div key={i} className="h-12 w-full animate-pulse rounded-xl bg-stone-100" />
            ))}
          </div>
        ) : rows.length === 0 ? (
          <div className="py-12 text-center text-stone-500">
            <span className="mx-auto mb-2 grid h-12 w-12 place-items-center rounded-2xl bg-cream text-stone-400">
              <Icon name="box" className="h-6 w-6" />
            </span>
            <p className="font-bold text-ink">No orders found</p>
            <p className="mt-1 text-xs text-stone-500 max-w-sm mx-auto">
              {allOrders.length
                ? "Try clearing the search filter or switching tabs."
                : "No orders yet. Orders booked by the AI agent from chats or created by you will appear here."}
            </p>
          </div>
        ) : (
          <ul className="divide-y divide-line/60">
            {rows.map((o) => (
              <li key={o.id}>
                <Link
                  href={`/orders/${o.id}`}
                  className="group flex items-center gap-4 p-4 transition-all hover:bg-stone-50/80"
                >
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-sm font-bold text-ink group-hover:text-brand-dark transition-colors">
                        {o.code}
                      </span>
                      <ChannelBadge channel={o.source} />
                    </div>
                    <p className="mt-0.5 truncate text-xs text-stone-600">
                      <b className="font-semibold text-ink">{o.customer_name}</b> · {timeAgo(o.created_at)}
                    </p>
                  </div>
                  <div className="text-right">
                    <p className="font-display text-sm font-bold text-ink">{rupees(o.total_paise)}</p>
                    <div className="mt-1 flex items-center justify-end gap-1.5">
                      <StatusBadge status={o.status} />
                      <Badge tone={o.payment_status === "paid" ? "green" : "amber"}>
                        {o.payment_status}
                      </Badge>
                    </div>
                  </div>
                  <span className="grid h-7 w-7 place-items-center rounded-lg text-stone-300 group-hover:text-ink transition-colors">
                    <Icon name="arrow" className="h-4 w-4" />
                  </span>
                </Link>
              </li>
            ))}
          </ul>
        )}
      </Card>

      {voiceModalOpen && (
        <VoiceOrderModal
          onClose={() => setVoiceModalOpen(false)}
          onOrderCreated={() => reload()}
        />
      )}
    </div>
  );
}
