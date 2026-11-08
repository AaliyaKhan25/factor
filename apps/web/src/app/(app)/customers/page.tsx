"use client";
import { api, Customer } from "@/lib/api";
import { initials, rupees } from "@/lib/format";
import { usePolling } from "@/hooks/usePolling";
import Card from "@/components/ui/Card";

export default function CustomersPage() {
  const { data, error, loading } = usePolling(() => api<Customer[]>("/customers"), 15000);
  if (error && !data) return <p className="rounded-xl bg-white p-4 text-stone-600">{error.includes("Missing permission") ? "Ask the owner for access to customers." : error}</p>;
  return (
    <div className="mx-auto max-w-4xl space-y-4">
      <h1 className="font-serif text-3xl font-bold">Customers</h1>
      <Card className="!p-0">
        {loading ? <p className="p-6 text-stone-500">Loading…</p> : !data?.length ? (
          <p className="p-8 text-center text-stone-500">Customers appear here when they message you or place an order.</p>
        ) : (
          <ul className="divide-y divide-line">
            {data.map((c) => (
              <li key={c.id} className="flex items-center gap-3 p-4">
                <span className="grid h-10 w-10 place-items-center rounded-full bg-brand-soft text-sm font-bold text-brand-dark">{initials(c.name)}</span>
                <div className="min-w-0 flex-1"><p className="truncate font-bold">{c.name}</p><p className="truncate text-sm text-stone-500">{[c.handle, c.phone].filter(Boolean).join(" · ") || "No contact"}</p></div>
                <div className="text-right"><p className="font-bold">{rupees(c.spent_paise)}</p><p className="text-xs text-stone-500">{c.orders} {c.orders === 1 ? "order" : "orders"}</p></div>
              </li>
            ))}
          </ul>
        )}
      </Card>
    </div>
  );
}
