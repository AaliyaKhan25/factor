"use client";

import Link from "next/link";
import Card from "@/components/ui/Card";
import Icon from "@/components/ui/Icon";

interface TodoItem {
  kind: string;
  title: string;
  detail: string;
  href: string;
}

interface Props {
  items: TodoItem[];
  businessName?: string;
}

export default function ActionCenter({ items, businessName }: Props) {
  const getBadgeStyle = (kind: string) => {
    switch (kind) {
      case "inbox":
        return { bg: "bg-brand-soft", text: "text-brand-dark", icon: "inbox", label: "DM Reply" };
      case "payments":
        return { bg: "bg-amber-100", text: "text-amber-800", icon: "wallet", label: "Collection" };
      case "ship":
        return { bg: "bg-sky-100", text: "text-sky-800", icon: "truck", label: "Dispatch" };
      case "orders":
        return { bg: "bg-emerald-100", text: "text-emerald-800", icon: "box", label: "New Order" };
      default:
        return { bg: "bg-stone-100", text: "text-stone-700", icon: "spark", label: "Task" };
    }
  };

  return (
    <Card className="flex flex-col">
      <div className="flex items-center justify-between border-b border-line/60 pb-3">
        <div className="flex items-center gap-2">
          <span className="grid h-7 w-7 place-items-center rounded-lg bg-amber-100 text-amber-800">
            <Icon name="clock" className="h-4 w-4" />
          </span>
          <div>
            <h2 className="font-display text-base font-bold text-ink">Action Required</h2>
            <p className="text-xs text-stone-500">Tasks requiring owner attention</p>
          </div>
        </div>
        {items.length > 0 ? (
          <span className="flex items-center gap-1.5 rounded-full bg-amber-100 px-2.5 py-0.5 text-xs font-bold text-amber-900 animate-pulse-slow">
            <span className="h-1.5 w-1.5 rounded-full bg-amber-600" />
            {items.length} pending
          </span>
        ) : (
          <span className="flex items-center gap-1 rounded-full bg-brand-soft px-2.5 py-0.5 text-xs font-bold text-brand-dark">
            <Icon name="check" className="h-3 w-3" /> All caught up
          </span>
        )}
      </div>

      <div className="mt-3 flex-1">
        {items.length > 0 ? (
          <ul className="divide-y divide-line/60">
            {items.map((t, idx) => {
              const meta = getBadgeStyle(t.kind);
              return (
                <li key={idx}>
                  <Link
                    href={t.href}
                    className="group flex items-center gap-3 py-3 transition-colors hover:bg-cream/40 px-2 rounded-xl"
                  >
                    <span
                      className={`grid h-10 w-10 shrink-0 place-items-center rounded-xl ${meta.bg} ${meta.text} shadow-xs transition-transform group-hover:scale-105`}
                    >
                      <Icon name={meta.icon} className="h-5 w-5" />
                    </span>
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-2">
                        <span className="block text-sm font-bold text-ink group-hover:text-brand-dark">
                          {t.title}
                        </span>
                        <span className={`text-[10px] font-semibold uppercase tracking-wider px-1.5 py-0.2 rounded-md ${meta.bg} ${meta.text}`}>
                          {meta.label}
                        </span>
                      </div>
                      <span className="block truncate text-xs text-stone-500">{t.detail}</span>
                    </div>
                    <span className="grid h-8 w-8 place-items-center rounded-lg bg-stone-100 text-stone-400 group-hover:bg-brand group-hover:text-ink transition-all">
                      <Icon name="arrow" className="h-4 w-4" />
                    </span>
                  </Link>
                </li>
              );
            })}
          </ul>
        ) : (
          <div className="flex flex-col items-center justify-center rounded-xl bg-cream/50 py-8 text-center">
            <span className="grid h-12 w-12 place-items-center rounded-2xl bg-brand-soft text-brand-dark mb-2">
              <Icon name="check" className="h-6 w-6" />
            </span>
            <p className="text-sm font-bold text-ink">Zero pending bottlenecks</p>
            <p className="mt-1 text-xs text-stone-500 max-w-xs">
              All messages are answered, payments logged, and orders dispatched at {businessName || "your workspace"}.
            </p>
          </div>
        )}
      </div>

      {/* Quick Navigation Footer */}
      <div className="mt-4 pt-3 border-t border-line/60 flex items-center justify-between text-xs text-stone-500">
        <Link href="/inbox" className="hover:text-brand-dark font-semibold flex items-center gap-1">
          <Icon name="inbox" className="h-3.5 w-3.5" /> DMs
        </Link>
        <span className="text-stone-300">·</span>
        <Link href="/orders" className="hover:text-brand-dark font-semibold flex items-center gap-1">
          <Icon name="box" className="h-3.5 w-3.5" /> All Orders
        </Link>
        <span className="text-stone-300">·</span>
        <Link href="/customers" className="hover:text-brand-dark font-semibold flex items-center gap-1">
          <Icon name="users" className="h-3.5 w-3.5" /> Customers
        </Link>
      </div>
    </Card>
  );
}
