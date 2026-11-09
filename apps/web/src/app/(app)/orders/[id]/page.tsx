"use client";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useState } from "react";
import { api, OrderDetail } from "@/lib/api";
import { clock, parseTime, rupees } from "@/lib/format";
import { usePolling } from "@/hooks/usePolling";
import Badge from "@/components/ui/Badge";
import Button from "@/components/ui/Button";
import Card from "@/components/ui/Card";
import ChannelBadge from "@/components/ui/ChannelBadge";
import ErrorText from "@/components/ui/ErrorText";
import StatusBadge from "@/components/orders/StatusBadge";
import Icon from "@/components/ui/Icon";
import CourierTracking from "@/components/orders/CourierTracking";

const STAGES = ["new", "confirmed", "packed", "shipped", "delivered"];

const LABEL: Record<string, string> = { confirmed: "Confirm order", packed: "Mark packed", shipped: "Mark shipped", delivered: "Mark delivered", cancelled: "Cancel order" };

export default function OrderDetailPage() {
  const { id } = useParams<{ id: string }>();
  const { data: o, error, reload } = usePolling(() => api<OrderDetail>(`/orders/${id}`), 6000, id);
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function move(status: string) {
    if (status === "cancelled" && !confirm("Cancel this order? Stock goes back to the catalog.")) return;
    setBusy(true);
    setErr(null);
    try { await api(`/orders/${id}/status`, { body: { status } }); await reload(); } catch (e) { setErr(e instanceof Error ? e.message : "Failed"); } finally { setBusy(false); }
  }

  if (error && !o) return <p className="rounded-xl bg-white p-4 text-stone-600">{error}</p>;
  if (!o) return <p className="text-stone-500">Loading…</p>;
  const forward = o.next_statuses.filter((s) => s !== "cancelled");
  const canCancel = o.next_statuses.includes("cancelled");

  return (
    <div className="mx-auto max-w-3xl space-y-4">
      <Link href="/orders" className="text-sm font-semibold text-brand-dark">← All orders</Link>
      <div className="flex flex-wrap items-center gap-3">
        <h1 className="font-display text-3xl font-extrabold tracking-tight text-ink">{o.code}</h1>
        <StatusBadge status={o.status} /><Badge tone={o.payment_status === "paid" ? "green" : "amber"}>{o.payment_status}</Badge><ChannelBadge channel={o.source} />
      </div>

      {/* Visual Order Progress Bar Stepper */}
      <Card className="!p-4">
        <p className="text-[11px] font-bold uppercase tracking-wider text-stone-500 mb-3">Fulfillment Progress</p>
        <div className="flex items-center justify-between relative px-2">
          <div className="absolute top-4 left-6 right-6 h-1 bg-stone-200 -z-0" />
          {STAGES.map((step, idx) => {
            const currentIdx = STAGES.indexOf(o.status);
            const isCompleted = o.status !== "cancelled" && currentIdx > idx;
            const isCurrent = o.status === step;
            const isCancelled = o.status === "cancelled";

            return (
              <div key={step} className="flex flex-col items-center relative z-10">
                <span
                  className={`grid h-8 w-8 place-items-center rounded-full text-xs font-bold transition-all shadow-xs ${
                    isCurrent
                      ? "bg-brand text-brand-dark ring-4 ring-brand-soft ring-offset-1 font-bold scale-110"
                      : isCompleted
                      ? "bg-brand-dark text-brand-soft"
                      : isCancelled && idx === currentIdx
                      ? "bg-red-500 text-white"
                      : "bg-white text-stone-400 border border-line"
                  }`}
                >
                  {isCompleted ? <Icon name="check" className="h-4 w-4" /> : idx + 1}
                </span>
                <span
                  className={`mt-1.5 text-[10px] font-semibold capitalize ${
                    isCurrent ? "font-bold text-ink" : "text-stone-500"
                  }`}
                >
                  {step}
                </span>
              </div>
            );
          })}
        </div>
      </Card>

      <Card>
        <p className="text-sm text-stone-500">Customer</p>
        <p className="font-bold">{o.customer.name}</p>
        <p className="text-sm text-stone-600">{[o.customer.handle, o.customer.phone].filter(Boolean).join(" · ") || "No contact saved"}</p>
        {o.note ? <p className="mt-2 text-sm text-stone-600">Note: {o.note}</p> : null}
      </Card>

      <CourierTracking orderId={o.id} tracking={o.tracking} onUpdated={() => void reload()} />
      {o.linked_conversation ? <Card className="flex flex-wrap items-center justify-between gap-3"><div><p className="text-xs text-stone-500">Linked customer chat</p><p className="font-semibold">{o.linked_conversation.display_name}</p></div><Link href={`/inbox?conversation=${o.linked_conversation.id}`} className="rounded-xl bg-brand-soft px-3 py-2 text-sm font-semibold text-brand-dark">Open chat</Link></Card> : null}

      <Card>
        <ul className="divide-y divide-line">
          {o.items.map((i, k) => (
            <li key={k} className="flex justify-between py-2 text-sm"><span>{i.quantity} × {i.name}</span><span>{rupees(i.unit_price_paise * i.quantity)}</span></li>
          ))}
        </ul>
        <p className="mt-2 flex justify-between border-t border-line pt-3 text-lg font-bold"><span>Total</span><span>{rupees(o.total_paise)}</span></p>
      </Card>

      {forward.length || canCancel ? (
        <Card className="space-y-3">
          <ErrorText message={err} />
          <div className="flex flex-wrap gap-2">
            {forward.map((s) => <Button key={s} disabled={busy} onClick={() => move(s)}>{LABEL[s]}</Button>)}
            {canCancel ? <Button variant="danger" disabled={busy} onClick={() => move("cancelled")}>{LABEL.cancelled}</Button> : null}
          </div>
        </Card>
      ) : null}

      <Card>
        <h2 className="font-serif text-xl font-bold">Timeline</h2>
        <p className="text-sm text-stone-500">Every step is recorded and cannot be edited. This is your evidence if a customer disputes something.</p>
        <ol className="mt-4 space-y-4 border-l-2 border-brand pl-5">
          {o.events.map((e, k) => (
            <li key={k} className="relative">
              <span className="absolute -left-[27px] top-1 h-3 w-3 rounded-full bg-brand-dark" />
              <p className="text-sm font-bold capitalize">{e.kind}</p>
              <p className="text-xs text-stone-500">{parseTime(e.created_at).toLocaleDateString("en-IN", { day: "numeric", month: "short" })}, {clock(e.created_at)}{e.detail ? ` · ${e.detail}` : ""}</p>
            </li>
          ))}
        </ol>
      </Card>
    </div>
  );
}
