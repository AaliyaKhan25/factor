"use client";
import { FormEvent, useState } from "react";
import { api, CatalogItem } from "@/lib/api";
import { rupees } from "@/lib/format";
import { useAuth } from "@/lib/auth";
import { usePolling } from "@/hooks/usePolling";
import Badge from "@/components/ui/Badge";
import Button from "@/components/ui/Button";
import Card from "@/components/ui/Card";
import ErrorText from "@/components/ui/ErrorText";
import Input, { fieldClass } from "@/components/ui/Input";
import Modal from "@/components/ui/Modal";

function ItemForm({ item, onDone }: { item?: CatalogItem; onDone: () => void }) {
  const [name, setName] = useState(item?.name ?? "");
  const [kind, setKind] = useState<"ready_stock" | "made_to_order">(item?.kind ?? "ready_stock");
  const [price, setPrice] = useState(item ? String(item.price_paise / 100) : "");
  const [qty, setQty] = useState(String(item?.quantity ?? 1));
  const [cap, setCap] = useState(String(item?.capacity ?? 5));
  const [lead, setLead] = useState(item?.lead_time_days != null ? String(item.lead_time_days) : "");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    const price_paise = Math.round(parseFloat(price) * 100);
    const leadDays = lead.trim() === "" ? null : parseInt(lead);
    try {
      if (item) {
        await api(`/catalog/${item.id}`, { method: "PATCH", body: { name, price_paise, lead_time_days: leadDays, ...(item.kind === "ready_stock" ? { quantity: parseInt(qty) } : { capacity: parseInt(cap) }) } });
      } else {
        await api("/catalog", { body: { name, kind, price_paise, lead_time_days: leadDays, ...(kind === "ready_stock" ? { quantity: parseInt(qty) } : { capacity: parseInt(cap) }) } });
      }
      onDone();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed");
      setBusy(false);
    }
  }

  return (
    <form onSubmit={submit} className="space-y-3">
      <Input label="Item name" required value={name} onChange={(e) => setName(e.target.value)} />
      {!item ? (
        <label className="block">
          <span className="mb-1 block text-sm font-medium text-stone-700">How do you sell it?</span>
          <select className={fieldClass} value={kind} onChange={(e) => setKind(e.target.value as typeof kind)}>
            <option value="ready_stock">Ready stock (I have units)</option>
            <option value="made_to_order">Made to order (I make it after the order)</option>
          </select>
        </label>
      ) : null}
      <Input label="Price (₹)" type="number" min={0} step="0.01" required value={price} onChange={(e) => setPrice(e.target.value)} />
      {(item?.kind ?? kind) === "ready_stock"
        ? <Input label="Units in stock" type="number" min={0} required value={qty} onChange={(e) => setQty(e.target.value)} />
        : <Input label="How many orders can you have open at once?" type="number" min={1} required value={cap} onChange={(e) => setCap(e.target.value)} hint="The agent stops taking orders when you are full." />}
      <Input label="Days to make or ship (optional)" type="number" min={0} value={lead} onChange={(e) => setLead(e.target.value)} />
      <ErrorText message={error} />
      <Button type="submit" disabled={busy} className="w-full">{busy ? "Saving…" : item ? "Save changes" : "Add item"}</Button>
    </form>
  );
}

export default function CatalogPage() {
  const { business } = useAuth();
  const { data, loading, reload } = usePolling(() => api<CatalogItem[]>("/catalog"), 10000);
  const [editing, setEditing] = useState<CatalogItem | "new" | null>(null);
  const canEdit = business?.your_permissions.includes("edit_prices");

  async function remove(i: CatalogItem) {
    if (!confirm(`Remove ${i.name} from the catalog? Past orders keep it.`)) return;
    await api(`/catalog/${i.id}`, { method: "PATCH", body: { active: false } });
    reload();
  }

  return (
    <div className="mx-auto max-w-5xl space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="font-serif text-3xl font-bold">Catalog</h1>
          <p className="text-sm text-stone-600">What the agent can quote and book. Prices and stock come only from here.</p>
        </div>
        {canEdit ? <Button onClick={() => setEditing("new")}>Add item</Button> : null}
      </div>
      {loading ? <p className="text-stone-500">Loading…</p> : !data?.length ? (
        <Card className="text-center text-stone-600">Your catalog is empty. Add what you sell so the agent can answer price and stock questions.</Card>
      ) : (
        <div className="grid gap-3 sm:grid-cols-2">
          {data.map((i) => (
            <Card key={i.id}>
              <div className="flex items-start justify-between gap-2">
                <div><p className="font-bold">{i.name}</p><Badge tone={i.kind === "ready_stock" ? "lime" : "blue"}>{i.kind === "ready_stock" ? "Ready stock" : "Made to order"}</Badge></div>
                <p className="font-serif text-2xl font-bold">{rupees(i.price_paise)}</p>
              </div>
              <p className="mt-3 text-sm text-stone-600">
                {i.kind === "ready_stock" ? `${i.available} in stock` : `${i.available} of ${i.capacity} slots free`}
                {i.lead_time_days != null ? ` · ${i.lead_time_days} days` : ""}
              </p>
              {canEdit ? <div className="mt-3 flex gap-2"><Button variant="secondary" onClick={() => setEditing(i)}>Edit</Button><Button variant="ghost" onClick={() => remove(i)}>Remove</Button></div> : null}
            </Card>
          ))}
        </div>
      )}
      {editing ? (
        <Modal title={editing === "new" ? "Add item" : "Edit item"} onClose={() => setEditing(null)}>
          <ItemForm item={editing === "new" ? undefined : editing} onDone={() => { setEditing(null); reload(); }} />
        </Modal>
      ) : null}
    </div>
  );
}
