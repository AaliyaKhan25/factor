"use client";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth";
import { api, InboxCounts } from "@/lib/api";
import { initials } from "@/lib/format";
import { usePolling } from "@/hooks/usePolling";
import Brand from "@/components/ui/Brand";
import Icon from "@/components/ui/Icon";
import FloatingVoiceButton from "@/components/voice/FloatingVoiceButton";

type Item = { href: string; label: string; icon: string; badge?: number; admin?: boolean };

export default function AppShell({ children }: { children: React.ReactNode }) {
  const { business, isAdmin, user } = useAuth();
  const path = usePathname();
  const router = useRouter();
  const counts = usePolling(() => api<InboxCounts>("/inbox/counts"), 5000);
  const needs = counts.data?.needs_owner ?? 0;

  const items: Item[] = [
    { href: "/dashboard", label: "Overview", icon: "home" },
    { href: "/inbox", label: "Inbox", icon: "inbox", badge: needs },
    { href: "/orders", label: "Orders", icon: "box" },
    { href: "/catalog", label: "Catalog", icon: "tag" },
    { href: "/customers", label: "Customers", icon: "users" },
    { href: "/setup/team", label: "Team", icon: "team", admin: true },
    { href: "/settings", label: "Settings", icon: "gear" },
  ].filter((i) => !i.admin || isAdmin);

  const mobile = items.filter((i) => ["/dashboard", "/inbox", "/orders", "/catalog", "/settings"].includes(i.href));
  const active = (href: string) => path === href || path.startsWith(href + "/");
  const current = items.find((i) => active(i.href))?.label ?? "Workspace";

  return (
    <div className="min-h-screen md:pl-64">
      <aside className="fixed inset-y-0 left-0 hidden w-64 flex-col border-r border-line bg-white p-4 md:flex">
        <div className="px-2 pb-5 pt-2"><Brand /></div>
        <div className="flex items-center gap-3 rounded-2xl border border-line p-3">
          <span className="grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-brand-soft font-serif text-lg font-bold text-brand-dark">
            {initials(business?.name ?? "")}
          </span>
          <div className="min-w-0">
            <p className="truncate text-sm font-bold">{business?.name}</p>
            <p className="text-xs text-stone-500">{isAdmin ? "Owner workspace" : "Team member"}</p>
          </div>
        </div>
        <button
          onClick={() => router.push("/orders/new")}
          className="mt-3 flex min-h-11 items-center gap-2 rounded-xl bg-brand px-4 text-sm font-bold text-ink hover:bg-brand-hover"
        >
          <Icon name="plus" className="h-4 w-4" /> Create order
        </button>
        <p className="mb-1 mt-6 px-3 text-[11px] font-bold uppercase tracking-widest text-stone-400">Workspace</p>
        <nav className="flex-1 space-y-1">
          {items.map((i) => (
            <Link
              key={i.href}
              href={i.href}
              className={`flex min-h-11 items-center gap-3 rounded-xl px-3 text-sm font-semibold ${
                active(i.href) ? "bg-brand-soft text-brand-dark" : "text-stone-600 hover:bg-stone-100"
              }`}
            >
              <Icon name={i.icon} />
              <span className="flex-1">{i.label}</span>
              {i.badge ? <span className="rounded-full bg-stone-200 px-2 py-0.5 text-xs">{i.badge}</span> : null}
            </Link>
          ))}
        </nav>
        <div className="flex items-center gap-3 border-t border-line px-2 pt-4">
          <span className="grid h-9 w-9 place-items-center rounded-full bg-brand-soft text-xs font-bold text-brand-dark">{initials(user?.name ?? "")}</span>
          <div className="min-w-0">
            <p className="truncate text-sm font-bold">{user?.name}</p>
            <p className="text-xs text-stone-500">{isAdmin ? "Business owner" : "Team"}</p>
          </div>
        </div>
      </aside>

      <header className="sticky top-0 z-30 flex items-center justify-between border-b border-line bg-cream/90 px-4 py-3 backdrop-blur md:px-8">
        <div className="md:hidden"><Brand /></div>
        <p className="hidden text-sm text-stone-500 md:block">
          Workspace <span className="mx-1 text-stone-300">›</span> <span className="font-semibold text-ink">{current}</span>
        </p>
        <Link href="/inbox" className="relative rounded-full border border-line bg-white p-2.5 text-stone-600" aria-label={`Inbox, ${needs} waiting`}>
          <Icon name="bell" className="h-5 w-5" />
          {needs ? <span className="absolute -right-0.5 -top-0.5 grid h-4 min-w-4 place-items-center rounded-full bg-red-500 px-1 text-[10px] font-bold text-white">{needs}</span> : null}
        </Link>
      </header>

      <main className="px-4 pb-28 pt-6 md:px-8 md:pb-10">{children}</main>

      <FloatingVoiceButton />

      <nav className="fixed inset-x-0 bottom-0 z-30 border-t border-line bg-white/95 backdrop-blur md:hidden">
        <ul className="flex">
          {mobile.map((i) => (
            <li key={i.href} className="flex-1">
              <Link href={i.href} className={`relative flex min-h-14 flex-col items-center justify-center gap-0.5 text-[11px] font-semibold ${active(i.href) ? "text-brand-dark" : "text-stone-500"}`}>
                <Icon name={i.icon} className="h-5 w-5" />
                {i.label}
                {i.badge ? <span className="absolute right-[22%] top-1.5 grid h-4 min-w-4 place-items-center rounded-full bg-red-500 px-1 text-[10px] font-bold text-white">{i.badge}</span> : null}
              </Link>
            </li>
          ))}
        </ul>
      </nav>
    </div>
  );
}
