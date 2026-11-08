"use client";
import { useCallback, useEffect, useState } from "react";
import { api, Member } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import Badge from "@/components/ui/Badge";
import Button from "@/components/ui/Button";
import Card from "@/components/ui/Card";
import ErrorText from "@/components/ui/ErrorText";

const PRESETS = [
  { value: "helper", label: "Helper", hint: "Sees orders, replies to chats" },
  { value: "packer", label: "Packer", hint: "Sees and updates orders" },
  { value: "manager", label: "Manager", hint: "Confirms payments, reviews cases, sees reports" },
  { value: "basic", label: "Basic", hint: "Minimal access" },
] as const;

type PresetValue = (typeof PRESETS)[number]["value"];
const body = (p: PresetValue) => (p === "basic" ? { role: "employee" } : { preset: p });

function tone(status: string) {
  return status === "active" ? "green" : status === "pending" ? "amber" : "gray";
}

function MemberCard({ m, onChange, onError }: { m: Member; onChange: () => void; onError: (e: string) => void }) {
  const [preset, setPreset] = useState<PresetValue>("helper");
  const [busy, setBusy] = useState(false);

  async function act(path: string, method: string, payload?: unknown) {
    setBusy(true);
    try {
      await api(path, { method, body: payload });
      onChange();
    } catch (e) {
      onError(e instanceof Error ? e.message : "Failed");
    } finally {
      setBusy(false);
    }
  }

  const isOwner = m.role === "admin";
  const select = (
    <select
      value={preset}
      onChange={(e) => setPreset(e.target.value as PresetValue)}
      className="min-h-11 w-full min-w-0 flex-1 rounded-xl border border-line bg-white px-3 text-sm"
      aria-label={`Access for ${m.name}`}
    >
      {PRESETS.map((p) => <option key={p.value} value={p.value}>{p.label}</option>)}
    </select>
  );

  const hint = PRESETS.find((p) => p.value === preset)?.hint;
  return (
    <Card>
      <div className="flex items-start justify-between gap-2">
        <div>
          <p className="font-bold">{m.name}</p>
          <p className="text-sm text-stone-600">{m.email}</p>
        </div>
        <Badge tone={isOwner ? "green" : tone(m.status)}>{isOwner ? "Owner" : m.status}</Badge>
      </div>

      {m.status === "pending" ? (
        <div className="mt-3 space-y-2">
          <div className="flex gap-2">{select}</div>
          <p className="text-xs text-stone-500">{hint}</p>
          <div className="flex gap-2">
            <Button className="flex-1" disabled={busy} onClick={() => act(`/team/members/${m.id}/approve`, "POST", body(preset))}>Approve</Button>
            <Button variant="danger" className="flex-1" disabled={busy} onClick={() => act(`/team/members/${m.id}/reject`, "POST")}>Reject</Button>
          </div>
        </div>
      ) : null}

      {m.status === "active" && !isOwner ? (
        <div className="mt-3 space-y-2">
          <p className="text-xs text-stone-500">Can: {m.permissions.length ? m.permissions.join(", ").replaceAll("_", " ") : "nothing yet"}</p>
          <div className="flex gap-2">
            {select}
            <Button variant="secondary" disabled={busy} onClick={() => act(`/team/members/${m.id}`, "PATCH", body(preset))}>Update</Button>
          </div>
          <Button variant="danger" className="w-full" disabled={busy} onClick={() => { if (confirm(`Remove ${m.name}?`)) act(`/team/members/${m.id}`, "DELETE"); }}>Remove from team</Button>
        </div>
      ) : null}
    </Card>
  );
}

export default function TeamPage() {
  const { isAdmin, business } = useAuth();
  const [members, setMembers] = useState<Member[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(() => {
    api<Member[]>("/team/members").then(setMembers).catch((e) => setError(e.message));
  }, []);
  useEffect(() => { if (isAdmin) load(); }, [isAdmin, load]);

  if (!isAdmin) return <p className="text-stone-600">Only the owner can manage the team.</p>;

  const pending = members?.filter((m) => m.status === "pending") ?? [];
  const team = members?.filter((m) => m.status === "active") ?? [];

  return (
    <div className="mx-auto max-w-2xl space-y-4">
      <h1 className="font-serif text-3xl font-bold">Team</h1>
      <ErrorText message={error} />
      {business?.business_code ? (
        <p className="text-sm text-stone-600">
          Business code: <span className="font-mono font-bold tracking-widest">{business.business_code}</span>
        </p>
      ) : null}

      <h3 className="pt-2 text-sm font-semibold uppercase tracking-wide text-stone-500">Waiting for approval ({pending.length})</h3>
      {pending.length === 0 ? <p className="text-sm text-stone-500">No requests.</p> : null}
      {pending.map((m) => <MemberCard key={m.id} m={m} onChange={load} onError={setError} />)}

      <h3 className="pt-2 text-sm font-semibold uppercase tracking-wide text-stone-500">On your team ({team.length})</h3>
      {team.map((m) => <MemberCard key={m.id} m={m} onChange={load} onError={setError} />)}
    </div>
  );
}
