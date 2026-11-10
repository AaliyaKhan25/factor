"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import Modal from "@/components/ui/Modal";
import Button from "@/components/ui/Button";
import Icon from "@/components/ui/Icon";
import ErrorText from "@/components/ui/ErrorText";
import { api } from "@/lib/api";
import { AudioRecorder, postVoiceAudio, postVoiceConfirmation } from "@/lib/voice";

type Result = {
  type: string; text?: string; transcript?: string; headline?: string; intent?: string;
  token?: string; action?: string; summary?: string; expires_at?: string;
  voice_confirmation_allowed?: boolean; audio_base64?: string; order_id?: number; order_code?: string;
  items?: { id?: number; name?: string; code?: string; customer_name?: string; kind?: string; quantity?: number | null; capacity?: number | null; available?: number; preview?: string; status?: string; total_paise?: number; payment_status?: string }[];
};
type Props = { onClose: () => void; onOrderCreated?: () => void };

export default function VoiceOrderModal({ onClose, onOrderCreated }: Props) {
  const recorder = useRef<AudioRecorder | null>(null);
  const [listening, setListening] = useState(false);
  const [transcribing, setTranscribing] = useState(false);
  const [level, setLevel] = useState(0);
  const [gnaniReady, setGnaniReady] = useState<boolean | null>(null);
  const [busy, setBusy] = useState(false);
  const [command, setCommand] = useState("");
  const [result, setResult] = useState<Result | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api<{ gnani_configured: boolean }>("/voice/status", { auth: false }).then((status) => setGnaniReady(status.gnani_configured)).catch(() => setGnaniReady(false));
  }, []);

  async function submitText() {
    setBusy(true); setError(""); setResult(null);
    try {
      const response = await api<Result>("/voice/commands", { body: { text: command } });
      setResult(response);
      if (response.audio_base64) new Audio(`data:audio/wav;base64,${response.audio_base64}`).play().catch(() => undefined);
    } catch (e) { setError(e instanceof Error ? e.message : "Could not process command"); }
    finally { setBusy(false); }
  }

  async function record() {
    if (listening) { recorder.current?.stop(); return; }
    if (!gnaniReady) { setError("Gnani voice is not configured on the API. Set GNANI_API_KEY or GNANI_TOKEN there and restart the API; typed commands still work."); return; }
    setError(""); setResult(null); setListening(true);
    const active = new AudioRecorder(); recorder.current = active;
    try {
      const { blob } = await active.start(setLevel);
      setListening(false); setTranscribing(true); setLevel(0);
      if (blob.size <= 44) throw new Error("I didn’t hear speech. Try again.");
      setBusy(true);
      const response = await postVoiceAudio(blob);
      setResult(response); if (response.transcript) setCommand(response.transcript);
      if (response.audio_base64) new Audio(`data:audio/wav;base64,${response.audio_base64}`).play().catch(() => undefined);
    } catch (e) { setError(e instanceof Error ? e.message : "Could not record audio"); }
    finally { setListening(false); setTranscribing(false); setLevel(0); setBusy(false); recorder.current = null; }
  }

  async function confirm(voice = false) {
    if (!result?.token) return;
    setBusy(true); setError("");
    try {
      const done = await api<Result>(`/voice/proposals/${result.token}/confirm`, { body: voice ? { voice_phrase: "yes" } : {} });
      setResult(done); onOrderCreated?.();
    } catch (e) { setError(e instanceof Error ? e.message : "Could not confirm action"); }
    finally { setBusy(false); }
  }

  async function confirmByVoice() {
    if (!result?.token) return;
    setError(""); setListening(true);
    const active = new AudioRecorder(); recorder.current = active;
    try {
      const { blob } = await active.start(setLevel);
      setListening(false); setTranscribing(true); setLevel(0);
      if (blob.size <= 44) throw new Error("I didn’t hear a confirmation.");
      setBusy(true);
      const done = await postVoiceConfirmation(blob, result.token);
      setResult(done); onOrderCreated?.();
    } catch (e) { setError(e instanceof Error ? e.message : "Could not confirm reply"); }
    finally { setListening(false); setTranscribing(false); setLevel(0); setBusy(false); recorder.current = null; }
  }

  return <Modal title="Voice assistant" onClose={() => { recorder.current?.stop(); onClose(); }}>
    <div className="space-y-4">
      <div className="flex items-center gap-3 rounded-2xl bg-brand-soft p-4 text-sm text-brand-dark">
        <span className="grid h-10 w-10 place-items-center rounded-xl bg-brand"><Icon name="mic"/></span>
        <span><b>Gnani speech in and out</b><small className="block">English, Hindi and Hinglish · mic audio stays behind the server API</small></span>
      </div>
      <div className="flex items-center gap-2">
        <Button type="button" onClick={() => void record()} disabled={busy || gnaniReady === null} variant={listening ? "danger" : "primary"}>
          <Icon name="mic" className="h-4 w-4"/>{listening ? "Stop listening" : "Speak a command"}
        </Button>
        <span className="text-xs text-stone-500">Stops after 5 seconds of silence or 30 seconds.</span>
      </div>
      {gnaniReady === false ? <p role="status" className="rounded-xl border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-900">Gnani speech is not configured on the API server. Set <code>GNANI_API_KEY</code> or <code>GNANI_TOKEN</code> there and restart it. Typed commands remain available.</p> : null}
      {(listening || transcribing) ? <div className="flex items-center gap-3 rounded-xl border border-line bg-cream/70 px-3 py-3" role="status" aria-live="polite">
        <div className="flex h-9 flex-1 items-center justify-center gap-1" aria-label={listening ? "Microphone audio level" : "Transcription in progress"}>
          {Array.from({ length: 24 }, (_, index) => {
            const wave = 5 + Math.round((listening ? level * 30 : 12) * (0.24 + Math.abs(Math.sin((index + 1) * 1.7))));
            return <span key={index} className={`w-1 rounded-full transition-[height,opacity] duration-100 ${transcribing ? "animate-pulse bg-amber-500" : "bg-brand-dark"}`} style={{ height: `${wave}px`, opacity: listening ? 0.45 + Math.min(level, 0.55) : 0.65, animationDelay: `${index * 35}ms` }} />;
          })}
        </div>
        <strong className="min-w-28 text-xs text-stone-600">{listening ? "Listening…" : "Transcribing with Gnani…"}</strong>
      </div> : null}
      <label className="block text-sm font-semibold">Or type a command<textarea value={command} onChange={(e) => setCommand(e.target.value)} rows={3} className="mt-1 w-full rounded-xl border border-line bg-white p-3 text-sm font-normal" placeholder="Read stock · Restock 4 scrunchies · Count 12 roses · Rahul ordered 2 totes · Confirm ORD-1001"/></label>
      <Button className="w-full" disabled={busy || !command.trim()} onClick={() => void submitText()}>{busy ? "Working…" : "Run command"}</Button>
      {result ? <section className="overflow-hidden rounded-2xl border border-line bg-white shadow-sm" aria-live="polite">
        {result.transcript ? <div className="border-b border-line bg-stone-50 px-4 py-2 text-xs text-stone-500"><span className="font-bold uppercase tracking-wide">Heard</span><span className="ml-2">“{result.transcript}”</span></div> : null}
        <div className="p-4">
          {result.type === "proposal" ? <><div className="flex items-center gap-2 text-brand-dark"><span className="grid h-8 w-8 place-items-center rounded-full bg-brand-soft"><Icon name="spark" size={16}/></span><div><p className="text-[10px] font-bold uppercase tracking-widest">Ready for review</p><p className="font-bold">{result.action?.replaceAll("_", " ") ?? "Proposed action"}</p></div></div><p className="mt-3 rounded-xl bg-cream p-3 text-sm leading-relaxed">{result.summary}</p><p className="mt-2 text-xs text-stone-500">Nothing changes until you confirm. This proposal expires in about two minutes.</p><Button className="mt-3 w-full" disabled={busy} onClick={() => void confirm()}>Confirm action</Button>{result.voice_confirmation_allowed ? <Button variant="secondary" className="mt-2 w-full" disabled={busy} onClick={() => void confirmByVoice()}>Speak “yes” to confirm the reply</Button> : null}</> : null}
          {result.type === "read_only" ? <><div className="flex items-center gap-2"><span className="grid h-9 w-9 place-items-center rounded-full bg-brand-soft text-brand-dark"><Icon name="search" size={17}/></span><div><p className="text-[10px] font-bold uppercase tracking-widest text-brand-dark">Search result</p><h3 className="font-bold">{result.headline ?? "Here’s what I found"}</h3></div></div><p className="mt-3 whitespace-pre-wrap rounded-xl bg-cream p-3 text-sm leading-relaxed">{result.text}</p>{result.items?.length ? <div className="mt-3 divide-y divide-line rounded-xl border border-line">{result.items.map((item, index) => <div className="flex items-center justify-between gap-3 px-3 py-2 text-xs" key={`${item.id ?? item.code ?? item.name ?? item.customer_name}-${index}`}><span className="font-semibold">{item.name ?? item.code ?? item.customer_name ?? "Result"}{item.code && item.customer_name ? <small className="ml-1 font-normal text-stone-500">· {item.customer_name}</small> : null}</span><span className="text-right text-stone-600">{item.preview ?? (item.kind === "made_to_order" ? `${item.available ?? 0} of ${item.capacity ?? 0} slots available` : item.quantity !== undefined && item.quantity !== null ? `${item.quantity} in stock` : item.total_paise !== undefined ? `${(item.total_paise / 100).toLocaleString("en-IN", { style: "currency", currency: "INR" })} · ${item.status ?? ""}${item.payment_status ? ` · ${item.payment_status} payment` : ""}` : item.status ?? (item.available !== undefined ? `${item.available} available` : ""))}</span></div>)}</div> : null}</> : null}
          {result.type === "needs_clarification" ? <><p className="text-[10px] font-bold uppercase tracking-widest text-amber-800">Need one more detail</p><p className="mt-2 rounded-xl bg-amber-50 p-3 text-sm leading-relaxed text-amber-950">{result.text}</p></> : null}
          {result.type === "completed" ? <><div className="flex items-center gap-2"><span className="grid h-8 w-8 place-items-center rounded-full bg-green-100 text-green-800"><Icon name="check" size={16}/></span><div><p className="text-[10px] font-bold uppercase tracking-widest text-green-800">Completed</p><p className="font-bold">{result.order_code ?? "Action saved"}</p></div></div><p className="mt-2 text-sm leading-relaxed">{result.text}</p>{result.order_id ? <Link className="mt-3 inline-flex rounded-xl border border-line px-3 py-2 text-sm font-semibold text-brand-dark" href={`/orders/${result.order_id}`} onClick={onClose}>Open order</Link> : null}</> : null}
        </div>
      </section> : null}
      <ErrorText message={error}/>
      <p className="text-[11px] text-stone-500">Changes are proposed before they run. Person approvals always need a tap.</p>
    </div>
  </Modal>;
}
