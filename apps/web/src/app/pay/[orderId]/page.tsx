"use client";

import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { API_URL, PaymentInfo } from "@/lib/api";
import { rupees } from "@/lib/format";

type PayPage = PaymentInfo & {
  business_name: string; order_code: string; order_status: string;
  payment_status: string; items: { name: string; quantity: number; unit_price_paise: number }[];
  total_paise: number;
};

export default function CustomerPayPage() {
  const { orderId } = useParams<{ orderId: string }>();
  const [payment, setPayment] = useState<PayPage | null>(null);
  const [error, setError] = useState("");
  useEffect(() => {
    const signature = new URLSearchParams(window.location.search).get("signature");
    if (!signature) { setError("This payment link is incomplete."); return; }
    fetch(`${API_URL}/payments/public/${orderId}?signature=${encodeURIComponent(signature)}`)
      .then(async (res) => { if (!res.ok) throw new Error("This payment link is invalid or has expired."); return res.json() as Promise<PayPage>; })
      .then(setPayment).catch((e: unknown) => setError(e instanceof Error ? e.message : "Could not load payment details."));
  }, [orderId]);

  return <main className="min-h-screen bg-cream px-4 py-10 text-ink"><div className="mx-auto max-w-lg">
    <header className="mb-8 flex items-center gap-2"><span className="grid h-9 w-9 place-items-center rounded-xl bg-brand font-bold">f</span><strong className="font-display text-xl">factor.</strong></header>
    {error ? <section className="rounded-2xl border border-line bg-white p-6"><h1 className="text-xl font-bold">Payment link unavailable</h1><p className="mt-2 text-stone-600">{error}</p></section> : !payment ? <p className="text-stone-500">Loading secure payment page…</p> : <section className="rounded-3xl border border-line bg-white p-6 shadow-sm">
      <p className="text-xs font-bold uppercase tracking-widest text-stone-500">{payment.business_name}</p><div className="mt-2 flex items-start justify-between gap-3"><div><h1 className="text-2xl font-extrabold">Pay for your order</h1><p className="mt-1 text-sm text-stone-500">{payment.order_code}</p></div><span className="rounded-full bg-amber-50 px-3 py-1 text-xs font-semibold capitalize text-amber-800">{payment.payment_status}</span></div>
      <div className="my-5 divide-y divide-line rounded-2xl border border-line px-4">{payment.items.map((line, i) => <div key={`${line.name}-${i}`} className="flex justify-between gap-4 py-3 text-sm"><span>{line.quantity} × {line.name}</span><span>{rupees(line.unit_price_paise * line.quantity)}</span></div>)}<div className="flex justify-between py-4 font-bold"><span>Total due</span><span>{rupees(payment.total_paise)}</span></div></div>
      <div className="grid place-items-center rounded-2xl bg-cream p-5"><img className="h-56 w-56" src={`${API_URL}/payments/public/${orderId}/qr?signature=${encodeURIComponent(new URLSearchParams(window.location.search).get("signature") ?? "")}`} alt={`UPI QR for ${payment.business_name}`} /><p className="mt-3 text-sm font-semibold">Scan with any UPI app</p><p className="mt-1 text-xs text-stone-500">Pay {payment.payee_name} · {payment.upi_id}</p></div>
      <a className="mt-4 flex w-full items-center justify-center rounded-xl bg-brand px-4 py-3 font-bold text-brand-dark" href={payment.upi_uri ?? undefined}>Open UPI app · {rupees(payment.total_paise)}</a>
      <p className="mt-4 text-center text-xs leading-relaxed text-stone-500">Your payment is complete after your bank confirms it. The business will verify receipt and update this order.</p>
    </section>}
    <footer className="mt-6 text-center text-xs text-stone-400">Secure payment request powered by Factor</footer>
  </div></main>;
}
