"use client";
import { FormEvent, useEffect, useRef, useState } from "react";
import { api, API_URL, CatalogItem, Conversation, ConversationDetail, InboxCounts } from "@/lib/api";
import { clock, initials, rupees, timeAgo } from "@/lib/format";
import { usePolling } from "@/hooks/usePolling";
import Badge from "@/components/ui/Badge";
import Button from "@/components/ui/Button";
import ChannelBadge from "@/components/ui/ChannelBadge";
import ErrorText from "@/components/ui/ErrorText";
import Icon from "@/components/ui/Icon";
import Input, { fieldClass } from "@/components/ui/Input";
import Modal from "@/components/ui/Modal";
import Link from "next/link";

type Tab = "needs_owner" | "agent" | "resolved";
const TABS: { key: Tab; label: string }[] = [
  { key: "needs_owner", label: "Needs you" },
  { key: "agent", label: "Handled by agent" },
  { key: "resolved", label: "Done" },
];

function SimulateModal({ onClose, onSent }: { onClose: () => void; onSent: (c: ConversationDetail) => void }) {
  const [channel, setChannel] = useState<"instagram" | "whatsapp">("instagram");
  const [name, setName] = useState("Riya");
  const [handle, setHandle] = useState("@riya.knits");
  const [text, setText] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const catalog = usePolling(() => api<CatalogItem[]>("/catalog"), 60000);
  const first = catalog.data?.[0]?.name;

  const presets = [
    ...(first ? [`how much is ${first}?`, `1 ${first} confirm`] : []),
    "can you make one with my dog's name on it?",
    "bhaiya thoda kam karo price",
    "my order was not delivered, I want a refund",
  ];

  async function send(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const h = channel === "whatsapp" && !handle.replace(/\D/g, "") ? "+91 90000 00001" : handle;
      onSent(await api<ConversationDetail>("/inbox/simulate", { body: { channel, handle: h, name, text } }));
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed");
      setBusy(false);
    }
  }

  return (
    <Modal title="Simulate an incoming DM" onClose={onClose}>
      <p className="mb-4 text-sm text-stone-600">Pretend a customer just messaged you. This is the same path a real Instagram or WhatsApp message takes once a channel is connected.</p>
      <form onSubmit={send} className="space-y-3">
        <div className="grid grid-cols-2 gap-2">
          {(["instagram", "whatsapp"] as const).map((c) => (
            <button key={c} type="button" onClick={() => { setChannel(c); setHandle(c === "instagram" ? "@riya.knits" : "+91 90000 00001"); }}
              className={`min-h-10 rounded-xl border text-sm font-semibold ${channel === c ? "border-brand-dark bg-brand-soft" : "border-line bg-white"}`}>
              {c === "instagram" ? "Instagram" : "WhatsApp"}
            </button>
          ))}
        </div>
        <Input label="Customer name" value={name} onChange={(e) => setName(e.target.value)} />
        <Input label={channel === "instagram" ? "Instagram handle" : "Phone number"} value={handle} onChange={(e) => setHandle(e.target.value)} required />
        <div>
          <span className="mb-1 block text-sm font-medium text-stone-700">Message</span>
          <textarea className={fieldClass + " py-2"} rows={3} required value={text} onChange={(e) => setText(e.target.value)} placeholder="Type a message or pick one below" />
          <div className="mt-2 flex flex-wrap gap-2">
            {presets.map((p) => <button key={p} type="button" onClick={() => setText(p)} className="rounded-full border border-line bg-cream px-3 py-1 text-xs text-stone-700 hover:bg-brand-soft">{p}</button>)}
          </div>
        </div>
        <ErrorText message={error} />
        <Button type="submit" disabled={busy} className="w-full">{busy ? "Sending…" : "Send message"}</Button>
      </form>
    </Modal>
  );
}

function Thread({ id, onBack, onChanged }: { id: number; onBack: () => void; onChanged: () => void }) {
  const { data: c, reload } = usePolling(() => api<ConversationDetail>(`/inbox/conversations/${id}`), 3000, String(id));
  const [text, setText] = useState("");
  const [error, setError] = useState<string | null>(null);
  const bottom = useRef<HTMLDivElement>(null);
  const count = c?.messages.length ?? 0;

  useEffect(() => { bottom.current?.scrollIntoView({ block: "end" }); }, [count, id]);

  async function post(path: string, body: unknown) {
    setError(null);
    try { await api(path, { body }); await reload(); onChanged(); } catch (e) { setError(e instanceof Error ? e.message : "Failed"); }
  }
  async function reply(e: FormEvent) {
    e.preventDefault();
    if (!text.trim()) return;
    const t = text;
    setText("");
    await post(`/inbox/conversations/${id}/reply`, { text: t });
  }

  if (!c) return <div className="grid h-full place-items-center text-stone-500">Loading…</div>;
  const mine = (s: string) => s !== "customer";

  return (
    <div className="flex h-full min-h-0 flex-col">
      <div className="flex flex-wrap items-center gap-3 border-b border-line p-4">
        <button onClick={onBack} className="rounded-full p-2 hover:bg-stone-100 md:hidden" aria-label="Back"><Icon name="back" /></button>
        <span className="grid h-10 w-10 place-items-center rounded-full bg-brand-soft text-sm font-bold text-brand-dark">{initials(c.display_name)}</span>
        <div className="min-w-0 flex-1">
          <p className="truncate font-bold">{c.display_name}</p>
          <p className="flex items-center gap-2 text-xs text-stone-500"><ChannelBadge channel={c.channel} /> {c.handle}</p>
        </div>
        <div className="flex gap-2">
          {c.status === "needs_owner" ? <Button variant="secondary" onClick={() => post(`/inbox/conversations/${id}/status`, { status: "agent" })}>Hand back to agent</Button> : null}
          {c.status === "agent" ? <Button variant="secondary" onClick={() => post(`/inbox/conversations/${id}/status`, { status: "needs_owner" })}>Take over</Button> : null}
          {c.status !== "resolved" ? <Button onClick={() => post(`/inbox/conversations/${id}/status`, { status: "resolved" })}><Icon name="check" className="h-4 w-4" /> Mark done</Button> : <Badge tone="green">Done</Badge>}
        </div>
      </div>

      {c.reason ? (
        <div className="flex flex-wrap items-center gap-2 border-b border-line bg-amber-50 px-4 py-2 text-sm">
          <b className="text-amber-900">{c.status === "needs_owner" ? "Why it needs you:" : "Note:"}</b> <span className="text-amber-900">{c.reason}</span>
          {c.orders.map((o) => <Link key={o.id} href={`/orders/${o.id}`} className="ml-auto rounded-full bg-white px-2.5 py-0.5 text-xs font-semibold text-brand-dark underline">{o.code} · {rupees(o.total_paise)}</Link>)}
        </div>
      ) : null}

      <div className="grid min-h-0 flex-1 lg:grid-cols-[minmax(0,1fr)_250px]">
        <div className="min-h-0 space-y-3 overflow-y-auto bg-cream/60 p-4">
          {c.messages.map((m) => (
            <div key={m.id} className={`flex ${mine(m.sender) ? "justify-end" : "justify-start"}`}>
              <div className={`max-w-[80%] rounded-2xl px-3.5 py-2 text-sm shadow-sm ${m.sender === "customer" ? "rounded-bl-sm bg-white" : m.sender === "agent" ? "rounded-br-sm bg-brand-soft" : "rounded-br-sm bg-brand"}`}>
                <p className="whitespace-pre-wrap">{m.text}</p>
                <p className="mt-1 text-[10px] uppercase tracking-wide text-stone-500">{m.sender === "customer" ? "Customer" : m.sender === "agent" ? "Agent" : "You"} · {clock(m.created_at)}</p>
              </div>
            </div>
          ))}
          <div className="space-y-3 lg:hidden">
            {c.orders.filter((order) => order.payment?.upi_ready && order.payment.qr_path).map((order) => <article key={order.id} className="mx-auto flex max-w-sm items-center gap-3 rounded-2xl border border-brand/30 bg-white p-3 shadow-sm">
              <img src={`${API_URL}${order.payment!.qr_path}`} alt={`Payment QR for ${order.code}`} className="h-24 w-24 rounded-lg border border-line p-1" />
              <div className="min-w-0"><p className="text-[10px] font-bold uppercase tracking-wide text-brand-dark">UPI QR · {order.code}</p><p className="mt-1 text-sm font-bold">{rupees(order.total_paise)}</p><p className="text-xs text-stone-500">Pay to {order.payment!.payee_name}</p><Link href={`/orders/${order.id}`} className="mt-2 inline-block text-xs font-semibold text-brand-dark underline">Open linked order</Link></div>
            </article>)}
          </div>
          <div ref={bottom} />
        </div>
        <aside className="hidden min-h-0 space-y-3 overflow-y-auto border-l border-line bg-white p-3 lg:block">
          <p className="text-xs font-bold uppercase tracking-wide text-stone-500">Linked orders</p>
          {c.orders.map((order) => <Link href={`/orders/${order.id}`} key={order.id} className="block rounded-xl border border-line bg-cream/50 p-3 hover:border-brand-dark">
            <span className="flex items-center justify-between gap-2"><b className="text-sm">{order.code}</b><span className="text-[10px] capitalize text-stone-500">{order.status}</span></span>
            <span className="mt-1 block text-xs text-stone-600">{rupees(order.total_paise)}</span>
            {order.payment?.upi_ready&&order.payment.qr_path?<span className="mt-2 flex items-center gap-2 rounded-lg bg-white p-2"><img src={`${API_URL}${order.payment.qr_path}`} alt={`Payment QR for ${order.code}`} className="h-20 w-20 rounded border border-line p-1"/><span className="min-w-0 text-[11px] text-stone-600"><b className="block text-ink">UPI QR attached</b>Pay to {order.payment.payee_name}<span className="mt-1 block">Scan for {rupees(order.total_paise)}</span></span></span>:null}
            {order.tracking ? <span className="mt-2 block rounded-lg bg-brand-soft p-2 text-xs"><b>{order.tracking.courier_name}</b><span className="block capitalize">{order.tracking.status.replaceAll("_", " ")}</span><span className="mt-0.5 block font-mono">AWB {order.tracking.awb}</span>{order.tracking.tracking_url ? <span className="mt-1 block underline">Open tracking ↗</span> : null}</span> : <span className="mt-2 block text-[11px] text-stone-400">No courier update yet</span>}
          </Link>)}
          {c.orders.length === 0 ? <p className="text-xs text-stone-400">No linked orders.</p> : null}
        </aside>
      </div>

      <form onSubmit={reply} className="border-t border-line p-3">
        <ErrorText message={error} />
        <div className="flex gap-2">
          <textarea value={text} onChange={(e) => setText(e.target.value)} rows={1} placeholder="Write a reply…" className={fieldClass + " resize-none py-2.5"} />
          <Button type="submit" aria-label="Send reply" disabled={!text.trim()}><Icon name="send" className="h-4 w-4" /></Button>
        </div>
        <p className="mt-1.5 text-[11px] text-stone-500">Replies are saved in this thread. Sending them back to Instagram or WhatsApp starts once the channel&apos;s send API is connected.</p>
      </form>
    </div>
  );
}

export default function InboxPage() {
  const [tab, setTab] = useState<Tab>("needs_owner");
  const [selected, setSelected] = useState<number | null>(null);
  const [sim, setSim] = useState(false);
  useEffect(() => {
    const conversation = Number(new URLSearchParams(window.location.search).get("conversation"));
    if (Number.isInteger(conversation) && conversation > 0) setSelected(conversation);
  }, []);
  const counts = usePolling(() => api<InboxCounts>("/inbox/counts"), 4000);
  const list = usePolling(() => api<Conversation[]>(`/inbox/conversations?bucket=${tab}`), 4000, tab);

  function refresh() { counts.reload(); list.reload(); }

  if (counts.error && !counts.data) return <p className="rounded-xl bg-white p-4 text-stone-600">{counts.error.includes("Missing permission") ? "Ask the owner for access to the inbox." : counts.error}</p>;

  return (
    <div className="mx-auto max-w-6xl">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="font-serif text-3xl font-bold">Inbox</h1>
          <p className="text-sm text-stone-600">Chats from your connected accounts. Updates by itself.</p>
        </div>
        <Button variant="secondary" onClick={() => setSim(true)}><Icon name="plus" className="h-4 w-4" /> Simulate a DM</Button>
      </div>

      <div className="grid h-[calc(100vh-15rem)] min-h-[460px] overflow-hidden rounded-2xl border border-line bg-white shadow-sm md:h-[calc(100vh-13rem)] grid-cols-1 md:grid-cols-[340px_minmax(0,1fr)]">
        <div className={`${selected ? "hidden md:flex" : "flex"} min-h-0 min-w-0 flex-col border-r border-line`}>
          <div className="grid grid-cols-3 gap-1 border-b border-line p-2">
            {TABS.map((t) => (
              <button key={t.key} onClick={() => { setTab(t.key); setSelected(null); }}
                className={`rounded-xl px-1 py-2 text-xs font-bold ${tab === t.key ? "bg-brand-soft text-brand-dark" : "text-stone-500 hover:bg-stone-100"}`}>
                {t.label}
                <span className={`ml-1 rounded-full px-1.5 ${t.key === "needs_owner" && (counts.data?.needs_owner ?? 0) > 0 ? "bg-red-500 text-white" : "bg-stone-200"}`}>{counts.data?.[t.key] ?? 0}</span>
              </button>
            ))}
          </div>
          <ul className="min-h-0 flex-1 overflow-y-auto">
            {(list.data ?? []).map((c) => (
              <li key={c.id}>
                <button onClick={() => setSelected(c.id)} className={`flex w-full min-w-0 gap-3 border-b border-line p-3 text-left hover:bg-stone-50 ${selected === c.id ? "bg-brand-soft/60" : ""}`}>
                  <span className="grid h-10 w-10 shrink-0 place-items-center rounded-full bg-brand-soft text-sm font-bold text-brand-dark">{initials(c.display_name)}</span>
                  <span className="min-w-0 flex-1">
                    <span className="flex items-center justify-between gap-2"><span className="truncate text-sm font-bold">{c.display_name}</span><span className="shrink-0 text-[11px] text-stone-400">{timeAgo(c.last_message_at)}</span></span>
                    <span className="block truncate text-xs text-stone-500">{c.last_preview}</span>
                    <span className="mt-1 flex items-center gap-1.5"><ChannelBadge channel={c.channel} />{c.reason ? <span className="truncate text-[11px] font-semibold text-amber-700">{c.reason}</span> : null}</span>
                  </span>
                </button>
              </li>
            ))}
            {list.data && list.data.length === 0 ? (
              <li className="p-6 text-center text-sm text-stone-500">
                {tab === "needs_owner" ? "Nothing needs you right now." : tab === "agent" ? "No chats are with the agent." : "No finished chats yet."}
                <br /><button onClick={() => setSim(true)} className="mt-2 font-semibold text-brand-dark underline">Simulate a DM</button>
              </li>
            ) : null}
          </ul>
        </div>
        <div className={`${selected ? "flex" : "hidden md:flex"} min-h-0 min-w-0 flex-col`}>
          {selected ? <Thread id={selected} onBack={() => setSelected(null)} onChanged={refresh} /> : <div className="grid h-full place-items-center p-6 text-center text-stone-500">Pick a chat to read it.</div>}
        </div>
      </div>

      {sim ? <SimulateModal onClose={() => setSim(false)} onSent={(c) => { setTab(c.status); setSelected(c.id); refresh(); }} /> : null}
    </div>
  );
}
