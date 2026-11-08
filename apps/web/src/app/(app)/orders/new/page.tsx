"use client";
import { useRouter } from "next/navigation";
import { FormEvent, useState } from "react";
import { api, CatalogItem, OrderDetail } from "@/lib/api";
import { rupees } from "@/lib/format";
import { usePolling } from "@/hooks/usePolling";
import Button from "@/components/ui/Button";
import Card from "@/components/ui/Card";
import ErrorText from "@/components/ui/ErrorText";
import Input, { fieldClass } from "@/components/ui/Input";

type Line = { item: string; qty: string };

export default function NewOrderPage() {
  const router = useRouter();
  const { data: catalog, loading } = usePolling(() => api<CatalogItem[]>("/catalog"), 30000);
  const [name, setName] = useState("");
  const [phone, setPhone] = useState("");
  const [handle, setHandle] = useState("");
  const [source, setSource] = useState("instagram");
  const [note, setNote] = useState("");
  const [lines, setLines] = useState<Line[]>([{ item: "", qty: "1" }]);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const items = catalog ?? [];
  const total = lines.reduce((sum, l) => {
    const it = items.find((i) => String(i.id) === l.item);
    return sum + (it ? it.price_paise * (parseInt(l.qty) || 0) : 0);
  }, 0);

  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const o = await api<OrderDetail>("/orders", {
        body: {
          customer: { name, phone: phone || null, handle: handle || null },
          source,
          note,
          items: lines.filter((l) => l.item).map((l) => ({ catalog_item_id: Number(l.item), quantity: parseInt(l.qty) || 1 })),
        },
      });
      router.push(`/orders/${o.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not create the order");
      setBusy(false);
    }
  }

  if (!loading && items.length === 0) {
    return <Card className="mx-auto max-w-xl text-center"><p className="text-stone-600">Add something to your catalog first, then you can create orders.</p><a href="/catalog" className="mt-3 inline-block font-semibold text-brand-dark underline">Go to catalog</a></Card>;
  }

  return (
    <form onSubmit={submit} className="mx-auto max-w-2xl space-y-4">
      <h1 className="font-serif text-3xl font-bold">New order</h1>
      <Card className="space-y-3">
        <h2 className="font-bold">Customer</h2>
        <Input label="Name" required value={name} onChange={(e) => setName(e.target.value)} />
        <div className="grid gap-3 sm:grid-cols-2">
          <Input label="Phone (optional)" inputMode="tel" value={phone} onChange={(e) => setPhone(e.target.value)} hint="Same number means the same customer" />
          <Input label="Instagram handle (optional)" value={handle} onChange={(e) => setHandle(e.target.value)} />
        </div>
        <label className="block">
          <span className="mb-1 block text-sm font-medium text-stone-700">Where did it come from?</span>
          <select className={fieldClass} value={source} onChange={(e) => setSource(e.target.value)}>
            <option value="instagram">Instagram</option><option value="whatsapp">WhatsApp</option><option value="manual">In person / other</option>
          </select>
        </label>
      </Card>
      <Card className="space-y-3">
        <h2 className="font-bold">Items</h2>
        {lines.map((l, i) => (
          <div key={i} className="flex gap-2">
            <select className={fieldClass} required value={l.item} onChange={(e) => setLines(lines.map((x, j) => (j === i ? { ...x, item: e.target.value } : x)))}>
              <option value="">Choose an item</option>
              {items.map((it) => <option key={it.id} value={it.id} disabled={it.available === 0}>{it.name} · {rupees(it.price_paise)} · {it.available} available</option>)}
            </select>
            <input className={fieldClass + " !w-20"} type="number" min={1} aria-label="Quantity" value={l.qty} onChange={(e) => setLines(lines.map((x, j) => (j === i ? { ...x, qty: e.target.value } : x)))} />
            {lines.length > 1 ? <button type="button" onClick={() => setLines(lines.filter((_, j) => j !== i))} className="px-2 text-stone-400" aria-label="Remove line">✕</button> : null}
          </div>
        ))}
        <Button type="button" variant="secondary" onClick={() => setLines([...lines, { item: "", qty: "1" }])}>Add another item</Button>
        <Input label="Note (optional)" value={note} onChange={(e) => setNote(e.target.value)} />
        <p className="flex justify-between border-t border-line pt-3 text-lg font-bold"><span>Total</span><span>{rupees(total)}</span></p>
        <p className="text-xs text-stone-500">Prices come from your catalog. The server checks stock when you save.</p>
      </Card>
      <ErrorText message={error} />
      <Button type="submit" disabled={busy} className="w-full">{busy ? "Saving…" : "Create order"}</Button>
    </form>
  );
}
