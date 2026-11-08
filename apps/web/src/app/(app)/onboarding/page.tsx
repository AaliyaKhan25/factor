"use client";
import { FormEvent, useState } from "react";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import Button from "@/components/ui/Button";
import Card from "@/components/ui/Card";
import Input from "@/components/ui/Input";
import ErrorText from "@/components/ui/ErrorText";

const TEMPLATES = [
  { value: "handmade", label: "Handmade / made to order" },
  { value: "general", label: "Ready stock" },
  { value: "rental", label: "Rentals" },
  { value: "tiffin", label: "Food / tiffin" },
];

export default function OnboardingPage() {
  const { user, hasPending, refresh, logout } = useAuth();
  const [mode, setMode] = useState<"create" | "join">("create");
  const [name, setName] = useState("");
  const [upi, setUpi] = useState("");
  const [template, setTemplate] = useState("handmade");
  const [code, setCode] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const wasRejected = user?.memberships.some((m) => m.status === "rejected" || m.status === "removed");

  async function run(fn: () => Promise<unknown>) {
    setBusy(true);
    setError(null);
    try {
      await fn();
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong");
    } finally {
      setBusy(false);
    }
  }

  const create = (e: FormEvent) => {
    e.preventDefault();
    run(() => api("/business", { body: { name, template, upi_id: upi.trim() || null } }));
  };
  const join = (e: FormEvent) => {
    e.preventDefault();
    run(() => api("/team/join", { body: { code } }));
  };

  return (
    <div className="mx-auto min-h-screen max-w-md px-4 py-10">
      <p className="text-sm font-semibold uppercase tracking-wide text-brand-dark">Factor</p>
      <h1 className="mt-1 font-serif text-3xl font-bold">Hi {user?.name.split(" ")[0]}</h1>

      {hasPending ? (
        <Card className="mt-6">
          <h2 className="font-bold">Waiting for approval</h2>
          <p className="mt-1 text-sm text-stone-600">
            Your request was sent. The owner has to approve it before you can see anything.
          </p>
          <Button variant="secondary" className="mt-4 w-full" onClick={() => run(async () => {})} disabled={busy}>
            Check again
          </Button>
        </Card>
      ) : (
        <>
          <p className="mt-1 text-stone-600">Start your own business, or join one with a code.</p>
          {wasRejected ? (
            <p className="mt-3 rounded-lg bg-brand-soft px-3 py-2 text-sm text-brand-dark">
              Your earlier request was not accepted. You can start your own business or ask again with a code.
            </p>
          ) : null}
          <div className="mt-5 grid grid-cols-2 gap-2 rounded-xl bg-stone-200/70 p-1">
            {(["create", "join"] as const).map((m) => (
              <button
                key={m}
                type="button"
                onClick={() => { setMode(m); setError(null); }}
                className={`min-h-10 rounded-lg text-sm font-semibold ${mode === m ? "bg-white shadow-sm" : "text-stone-600"}`}
              >
                {m === "create" ? "Start my business" : "Join with a code"}
              </button>
            ))}
          </div>

          {mode === "create" ? (
            <form onSubmit={create} className="mt-5 space-y-4">
              <Input label="Business name" required minLength={2} placeholder="e.g. Knot & Loop" value={name} onChange={(e) => setName(e.target.value)} />
              <label className="block">
                <span className="mb-1 block text-sm font-medium text-stone-700">What do you sell?</span>
                <select
                  value={template}
                  onChange={(e) => setTemplate(e.target.value)}
                  className="min-h-11 w-full rounded-xl border border-line bg-white px-3 text-base"
                >
                  {TEMPLATES.map((t) => <option key={t.value} value={t.value}>{t.label}</option>)}
                </select>
              </label>
              <Input label="UPI ID (optional)" placeholder="name@bank" value={upi} onChange={(e) => setUpi(e.target.value)} hint="Used later for payment links. You can add it in Settings." />
              <ErrorText message={error} />
              <Button type="submit" disabled={busy} className="w-full">{busy ? "Creating…" : "Create business"}</Button>
            </form>
          ) : (
            <form onSubmit={join} className="mt-5 space-y-4">
              <Input label="Business code" required placeholder="ABCD-1234" value={code} onChange={(e) => setCode(e.target.value)} hint="Ask the owner for the code. They must approve you." />
              <ErrorText message={error} />
              <Button type="submit" disabled={busy} className="w-full">{busy ? "Sending…" : "Send request"}</Button>
            </form>
          )}
        </>
      )}
      <button onClick={logout} className="mt-8 text-sm text-stone-500 underline">Sign out</button>
    </div>
  );
}
