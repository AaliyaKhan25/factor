"use client";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { API_URL, api, Channel } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { usePolling } from "@/hooks/usePolling";
import Button from "@/components/ui/Button";
import Card from "@/components/ui/Card";
import ChannelBadge from "@/components/ui/ChannelBadge";
import ErrorText from "@/components/ui/ErrorText";
import SheetsSettings from "@/components/settings/SheetsSettings";
import CourierSettings from "@/components/settings/CourierSettings";

function Channels() {
  const { data, reload } = usePolling(() => api<Channel[]>("/channels"), 30000);
  const [error, setError] = useState<string | null>(null);

  async function connect(channel: "instagram" | "whatsapp") {
    setError(null);
    try { await api("/channels", { body: { channel } }); await reload(); } catch (e) { setError(e instanceof Error ? e.message : "Failed"); }
  }
  async function remove(id: number) {
    if (!confirm("Disconnect this channel? Messages will stop arriving.")) return;
    await api(`/channels/${id}`, { method: "DELETE" });
    reload();
  }

  return (
    <Card className="space-y-4">
      <div>
        <h2 className="font-serif text-xl font-bold">Connect your inbox</h2>
        <p className="text-sm text-stone-600">Each connection gets a webhook address. Give it to Meta and customer DMs start arriving in your Inbox.</p>
      </div>
      <div className="flex flex-wrap gap-2">
        <Button onClick={() => connect("instagram")}>Connect Instagram</Button>
        <Button variant="secondary" onClick={() => connect("whatsapp")}>Connect WhatsApp</Button>
      </div>
      <ErrorText message={error} />
      {(data ?? []).map((c) => (
        <div key={c.id} className="rounded-xl border border-line bg-cream p-3 text-sm">
          <div className="flex items-center justify-between"><ChannelBadge channel={c.channel} /><button onClick={() => remove(c.id)} className="text-xs font-semibold text-red-700">Disconnect</button></div>
          <p className="mt-2 text-xs text-stone-500">Callback URL</p>
          <p className="break-all font-mono text-xs">{API_URL}{c.webhook_path}</p>
          <p className="mt-2 text-xs text-stone-500">Verify token</p>
          <p className="break-all font-mono text-xs">{c.verify_token}</p>
        </div>
      ))}
      <p className="rounded-lg bg-amber-50 p-3 text-xs text-amber-900">
        Before real DMs flow: Meta needs a public HTTPS address for the callback, and your Meta app needs approval for messaging. Until then, use <b>Simulate a DM</b> in the Inbox to demo the same flow.
      </p>
    </Card>
  );
}

export default function SettingsPage() {
  const { business, user, isAdmin, refresh, logout } = useAuth();
  const router = useRouter();
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  const [busy, setBusy] = useState(false);

  async function copy() {
    try { await navigator.clipboard.writeText(business?.business_code ?? ""); setCopied(true); setTimeout(() => setCopied(false), 1500); }
    catch { setError("Could not copy. Select the code and copy it by hand."); }
  }
  async function regenerate(singleUse: boolean) {
    if (!confirm("This cancels the current code. Anyone with the old code can no longer join. Continue?")) return;
    setBusy(true); setError(null);
    try { await api(`/business/code/regenerate?single_use=${singleUse}`, { method: "POST" }); await refresh(); }
    catch (e) { setError(e instanceof Error ? e.message : "Failed"); } finally { setBusy(false); }
  }

  return (
    <div className="mx-auto max-w-2xl space-y-4">
      <h1 className="font-serif text-3xl font-bold">Settings</h1>
      <Card>
        <p className="text-sm text-stone-500">Business</p>
        <p className="text-lg font-bold">{business?.name}</p>
        <p className="text-sm text-stone-600">UPI: {business?.upi_id ?? "not set"} · Signed in as {user?.email}</p>
        <div className="mt-3 flex gap-4 text-sm font-semibold text-brand-dark md:hidden">
          <Link href="/customers" className="underline">Customers</Link>
          {isAdmin ? <Link href="/setup/team" className="underline">Team</Link> : null}
        </div>
      </Card>
      {isAdmin ? <Channels /> : null}
      {isAdmin ? <SheetsSettings /> : null}
      {isAdmin ? <CourierSettings /> : null}
      {isAdmin ? (
        <Card>
          <p className="text-sm text-stone-600">Business code for your team</p>
          <p className="mt-1 font-mono text-2xl font-bold tracking-widest">{business?.business_code ?? "No active code"}</p>
          <div className="mt-3 flex flex-wrap gap-2">
            <Button variant="secondary" onClick={copy} disabled={!business?.business_code}>{copied ? "Copied" : "Copy"}</Button>
            <Button variant="secondary" disabled={busy} onClick={() => regenerate(false)}>New code</Button>
            <Button variant="secondary" disabled={busy} onClick={() => regenerate(true)}>New one-time code</Button>
          </div>
          <div className="mt-2"><ErrorText message={error} /></div>
        </Card>
      ) : null}
      <Button variant="danger" className="w-full" onClick={() => { logout(); router.replace("/login"); }}>Sign out</Button>
    </div>
  );
}
