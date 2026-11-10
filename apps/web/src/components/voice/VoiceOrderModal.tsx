"use client";

import { useRef, useState } from "react";
import Modal from "@/components/ui/Modal";
import Button from "@/components/ui/Button";
import Icon from "@/components/ui/Icon";
import ErrorText from "@/components/ui/ErrorText";
import { api } from "@/lib/api";
import { AudioRecorder, postVoiceAudio, postVoiceConfirmation } from "@/lib/voice";

type Result = { type: string; text?: string; transcript?: string; token?: string; summary?: string; expires_at?: string; voice_confirmation_allowed?: boolean; audio_base64?: string };
type Props = { onClose: () => void; onOrderCreated?: () => void };

export default function VoiceOrderModal({ onClose, onOrderCreated }: Props) {
  const recorder = useRef<AudioRecorder | null>(null);
  const [listening, setListening] = useState(false);
  const [transcribing, setTranscribing] = useState(false);
  const [level, setLevel] = useState(0);
  const [busy, setBusy] = useState(false);
  const [command, setCommand] = useState("");
  const [result, setResult] = useState<Result | null>(null);
  const [error, setError] = useState("");

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
        <Button type="button" onClick={() => void record()} disabled={busy} variant={listening ? "danger" : "primary"}>
          <Icon name="mic" className="h-4 w-4"/>{listening ? "Stop listening" : "Speak a command"}
        </Button>
        <span className="text-xs text-stone-500">Stops after 5 seconds of silence or 30 seconds.</span>
      </div>
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
      {result ? <div className="rounded-2xl border border-line bg-cream p-4" aria-live="polite">
        {result.transcript ? <p className="mb-2 text-xs text-stone-500">Heard: “{result.transcript}”</p> : null}
        {result.type === "proposal" ? <><p className="font-semibold">Review this action</p><p className="mt-1 text-sm">{result.summary}</p><p className="mt-2 text-xs text-stone-500">This confirmation expires in about two minutes and can be used once.</p><Button className="mt-3 w-full" disabled={busy} onClick={() => void confirm()}>Confirm with a tap</Button>{result.voice_confirmation_allowed ? <Button variant="secondary" className="mt-2 w-full" disabled={busy} onClick={() => void confirmByVoice()}>Speak “yes” to confirm the reply</Button> : null}</> : <p className="text-sm">{result.text ?? "Done."}</p>}
      </div> : null}
      <ErrorText message={error}/>
      <p className="text-[11px] text-stone-500">Changes are proposed before they run. Person approvals always need a tap.</p>
    </div>
  </Modal>;
}
