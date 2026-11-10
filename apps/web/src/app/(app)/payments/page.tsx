"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { api, API_URL, PendingPayment } from "@/lib/api";
import { clock, parseTime, rupees } from "@/lib/format";
import Button from "@/components/ui/Button";

export default function PaymentsPage() {
  const [rows, setRows] = useState<PendingPayment[]>([]);
  const [error, setError] = useState("");
  const [copied, setCopied] = useState<number | null>(null);
  useEffect(() => { api<PendingPayment[]>("/payments/pending").then(setRows).catch((e: unknown) => setError(e instanceof Error ? e.message : "Could not load pending payments.")); }, []);
  async function copy(row: PendingPayment) {
    if (!row.payment_link) return;
    await navigator.clipboard.writeText(row.payment_link); setCopied(row.id); window.setTimeout(() => setCopied(null), 1800);
  }
  return <main className="mx-auto max-w-5xl space-y-6">
    <header><p className="text-xs font-bold uppercase tracking-widest text-brand-dark">Money in</p><h1 className="mt-1 font-display text-3xl font-extrabold">Pending payments</h1><p className="mt-2 text-sm text-stone-500">Share a UPI payment page or scan its QR. Verify receipt in your bank before recording payment.</p></header>
    {error ? <p role="alert" className="rounded-xl bg-red-50 p-4 text-sm text-red-700">{error}</p> : rows.length === 0 ? <section className="rounded-2xl border border-line bg-white p-8 text-center"><h2 className="font-bold">You’re all caught up</h2><p className="mt-1 text-sm text-stone-500">Unpaid orders will appear here.</p></section> : <div className="space-y-4">{rows.map((row) => <article key={row.id} className="flex flex-wrap items-center gap-4 rounded-2xl border border-line bg-white p-4 shadow-sm">
      {row.qr_path ? <img className="h-28 w-28 rounded-xl border border-line bg-white p-1" src={`${API_URL}${row.qr_path}`} alt={`UPI payment QR for order ${row.code}`} /> : <div className="grid h-28 w-28 place-items-center rounded-xl bg-amber-50 p-3 text-center text-xs text-amber-800">Add your business UPI ID to create a QR</div>}
      <div className="min-w-48 flex-1"><div className="flex flex-wrap items-center gap-2"><Link href={`/orders/${row.id}`} className="font-bold text-brand-dark hover:underline">{row.code}</Link><span className="rounded-full bg-amber-50 px-2 py-1 text-xs capitalize text-amber-800">{row.payment_status}</span></div><p className="mt-1 text-sm">{row.customer_name} · <strong>{rupees(row.total_paise)}</strong></p><p className="mt-1 text-xs text-stone-500">Order {row.status} · {parseTime(row.created_at).toLocaleDateString("en-IN", { day: "numeric", month: "short" })} at {clock(row.created_at)}</p>{row.upi_ready ? <p className="mt-1 text-xs text-stone-500">Pay to {row.payee_name} · {row.upi_id}</p> : null}</div>
      <div className="flex gap-2">{row.upi_uri ? <a className="rounded-xl bg-brand px-3 py-2 text-sm font-semibold text-brand-dark" href={row.upi_uri}>Pay</a> : null}{row.payment_link ? <Button variant="secondary" onClick={() => void copy(row)}>{copied === row.id ? "Copied" : "Copy link"}</Button> : null}</div>
    </article>)}</div>}
  </main>;
}
