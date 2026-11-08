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
import Icon from "@/components/ui/Icon";

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
  const [search, setSearch] = useState("");
  const canEdit = business?.your_permissions.includes("edit_prices");

  async function remove(i: CatalogItem) {
    if (!confirm(`Remove ${i.name} from the catalog? Past orders keep it.`)) return;
    await api(`/catalog/${i.id}`, { method: "PATCH", body: { active: false } });
    reload();
  }

  const items = data ?? [];
  const filtered = items.filter((i) => !search || i.name.toLowerCase().includes(search.toLowerCase().trim()));

  const readyStockItems = items.filter((i) => i.kind === "ready_stock");
  const totalStockUnits = readyStockItems.reduce((acc, i) => acc + (i.available || 0), 0);
  const lowStockCount = items.filter((i) => i.kind === "ready_stock" && i.available <= 2).length;

  return (
    <div className="mx-auto max-w-5xl space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="font-display text-3xl font-extrabold tracking-tight text-ink">Catalog</h1>
          <p className="mt-0.5 text-xs text-stone-500">Products and pricing quoted and booked by the AI agent.</p>
        </div>
        {canEdit ? (
          <Button
            onClick={() => setEditing("new")}
            className="inline-flex items-center gap-1.5 shadow-sm hover:shadow-glow"
          >
            <Icon name="plus" className="h-4 w-4" /> Add item
          </Button>
        ) : null}
      </div>

      {/* Inventory Statistical Summary */}
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <Card className="!p-3.5">
          <p className="text-[10px] font-bold uppercase tracking-wider text-stone-500">Total Products</p>
          <p className="mt-1 font-display text-xl font-bold text-ink">{items.length}</p>
          <p className="text-[11px] text-stone-400">In catalog register</p>
        </Card>
        <Card className="!p-3.5">
          <p className="text-[10px] font-bold uppercase tracking-wider text-stone-500">Units in Stock</p>
          <p className="mt-1 font-display text-xl font-bold text-ink">{totalStockUnits}</p>
          <p className="text-[11px] text-stone-400">Ready to dispatch</p>
        </Card>
        <Card className="!p-3.5">
          <p className="text-[10px] font-bold uppercase tracking-wider text-stone-500">Made to Order</p>
          <p className="mt-1 font-display text-xl font-bold text-ink">
            {items.filter((i) => i.kind === "made_to_order").length}
          </p>
          <p className="text-[11px] text-stone-400">Custom capacity items</p>
        </Card>
        <Card className="!p-3.5">
          <div className="flex items-center justify-between">
            <p className="text-[10px] font-bold uppercase tracking-wider text-stone-500">Stock Status</p>
            {lowStockCount > 0 ? (
              <span className="text-[10px] font-bold text-amber-700 bg-amber-100 px-1.5 py-0.2 rounded-full">
                {lowStockCount} low
              </span>
            ) : (
              <span className="text-[10px] font-bold text-emerald-700">Healthy</span>
            )}
          </div>
          <p className="mt-1 font-display text-xl font-bold text-ink">
            {items.length - lowStockCount} / {items.length}
          </p>
          <p className="text-[11px] text-stone-400">Well-stocked items</p>
        </Card>
      </div>

      {/* Search Input */}
      {items.length > 0 && (
        <div className="relative max-w-sm">
          <input
            type="text"
            placeholder="Search catalog items..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="h-9 w-full rounded-xl border border-line bg-white pl-8 pr-3 text-xs placeholder:text-stone-400 focus:border-brand-dark focus:outline-none"
          />
          <span className="absolute left-2.5 top-2.5 text-stone-400">
            <Icon name="tag" className="h-4 w-4" />
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
      )}

      {loading ? (
        <div className="grid gap-3 sm:grid-cols-2">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="h-32 rounded-2xl bg-stone-100 animate-pulse" />
          ))}
        </div>
      ) : !filtered.length ? (
        <Card className="text-center py-10">
          <span className="mx-auto mb-2 grid h-12 w-12 place-items-center rounded-2xl bg-cream text-stone-400">
            <Icon name="tag" className="h-6 w-6" />
          </span>
          <p className="font-bold text-ink">
            {items.length ? "No items matching your search" : "Your catalog is empty"}
          </p>
          <p className="mt-1 text-xs text-stone-500 max-w-sm mx-auto">
            {items.length
              ? "Try typing a different item name."
              : "Add what you sell or make so the AI agent can quote prices and check stock automatically."}
          </p>
        </Card>
      ) : (
        <div className="grid gap-3 sm:grid-cols-2">
          {filtered.map((i) => (
            <Card key={i.id} hoverable className="space-y-3">
              <div className="flex items-start justify-between gap-2">
                <div>
                  <p className="font-bold text-ink text-base">{i.name}</p>
                  <div className="mt-1">
                    <Badge tone={i.kind === "ready_stock" ? "lime" : "blue"}>
                      {i.kind === "ready_stock" ? "Ready stock" : "Made to order"}
                    </Badge>
                  </div>
                </div>
                <p className="font-display text-2xl font-bold text-ink">{rupees(i.price_paise)}</p>
              </div>

              <div className="rounded-xl bg-cream/50 p-2.5 text-xs text-stone-600 flex items-center justify-between">
                <span>
                  {i.kind === "ready_stock" ? (
                    <span className={i.available <= 2 ? "font-bold text-amber-800" : "font-medium text-stone-700"}>
                      <b>{i.available}</b> units left in stock
                    </span>
                  ) : (
                    <span>
                      <b>{i.available}</b> of {i.capacity} custom slots free
                    </span>
                  )}
                </span>
                {i.lead_time_days != null && (
                  <span className="text-[11px] text-stone-400">⏱ {i.lead_time_days} days lead</span>
                )}
              </div>

              {canEdit ? (
                <div className="flex items-center gap-2 pt-1 border-t border-line/60">
                  <Button variant="secondary" className="!min-h-8 !text-xs" onClick={() => setEditing(i)}>
                    Edit
                  </Button>
                  <Button variant="ghost" className="!min-h-8 !text-xs text-stone-500" onClick={() => remove(i)}>
                    Remove
                  </Button>
                </div>
              ) : null}
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
