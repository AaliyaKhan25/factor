"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import Icon from "@/components/ui/Icon";
import VoiceOrderModal from "./VoiceOrderModal";
import { AudioRecorder, postVoiceAudio, postVoiceConfirmation } from "@/lib/voice";
import { repliesEnabled, setRepliesEnabled, speak, stopSpeaking } from "@/lib/speak";

type Phase = "idle" | "listening" | "thinking" | "speaking";
type Reply = {
  type: string; text?: string; transcript?: string; summary?: string; token?: string; path?: string; audio_base64?: string;
};

const LABEL: Record<Phase, string> = { idle: "Tap and speak", listening: "Listening…", thinking: "Working on it…", speaking: "Speaking…" };
const asMessage = (e: unknown) => (e instanceof Error ? e.message : "Something went wrong.");

/**
 * Hands-free control for the whole app. Tap once, then talk: it opens screens, answers questions, reads changes back,
 * waits for a spoken yes or no, and reads every error aloud. It keeps listening until you stay quiet or tap again.
 */
export default function FloatingVoiceButton() {
  const router = useRouter();
  const recorder = useRef<AudioRecorder | null>(null);
  const stopped = useRef(false);
  const [phase, setPhase] = useState<Phase>("idle");
  const [level, setLevel] = useState(0);
  const [panelOpen, setPanelOpen] = useState(false);
  const [heard, setHeard] = useState("");
  const [reply, setReply] = useState("");
  const [typing, setTyping] = useState(false);
  const [voiceReplies, setVoiceReplies] = useState(true);

  useEffect(() => { setVoiceReplies(repliesEnabled()); return () => { stopped.current = true; recorder.current?.stop(); stopSpeaking(); }; }, []);

  const active = phase !== "idle";

  async function say(text: string, audio?: string) {
    setReply(text);
    if (!repliesEnabled() || stopped.current) return;
    setPhase("speaking");
    await speak(text, audio);
  }

  /** Record one utterance. Returns null when nothing was said. */
  async function listen(): Promise<Blob | null> {
    setPhase("listening");
    const rec = new AudioRecorder();
    recorder.current = rec;
    try {
      const { blob } = await rec.start(setLevel);
      return blob.size > 44 + 6400 ? blob : null; // under about 0.2 s of audio counts as silence
    } finally { recorder.current = null; setLevel(0); }
  }

  /** After a proposal is read back, wait for a spoken yes or no. Two tries. */
  async function confirmByVoice(token: string): Promise<void> {
    for (let attempt = 0; attempt < 2 && !stopped.current; attempt++) {
      const blob = await listen();
      if (stopped.current) return;
      if (!blob) { await say("I did not hear a yes, so I changed nothing."); return; }
      setPhase("thinking");
      try {
        const done: Reply = await postVoiceConfirmation(blob, token);
        await handle(done);
        return;
      } catch (e) {
        const message = asMessage(e);
        if (/clear yes|cancel/i.test(message) && attempt === 0) { await say(`${message}. Say yes to confirm, or no to drop it.`); continue; }
        await say(message);
        return;
      }
    }
  }

  async function handle(res: Reply): Promise<void> {
    if (res.type === "navigate") {
      if (res.path === "back") router.back(); else if (res.path) router.push(res.path);
      await say(res.text ?? "Done.");
    } else if (res.type === "proposal" && res.token) {
      await say(`${res.summary ?? "Ready."} Say yes to confirm, or no.`);
      await confirmByVoice(res.token);
    } else if (res.type === "completed") {
      window.dispatchEvent(new Event("factor:changed"));
      router.refresh();
      await say(res.text ?? "Done.");
    } else {
      await say(res.text ?? "Done.", res.audio_base64);
    }
  }

  async function session() {
    stopped.current = false;
    setHeard(""); setReply("");
    let misses = 0;
    try {
      while (!stopped.current && misses < 2) {
        const blob = await listen();
        if (stopped.current) break;
        if (!blob) { if (misses === 0) await say("I did not hear anything. Tap and try again."); break; }
        setPhase("thinking");
        try {
          const res: Reply = await postVoiceAudio(blob);
          misses = 0;
          setHeard(res.transcript ?? "");
          await handle(res);
        } catch (e) {
          const message = asMessage(e);
          if (/did not hear/i.test(message)) break;
          misses++;
          await say(message);
        }
      }
    } catch (e) {
      const denied = e instanceof DOMException && (e.name === "NotAllowedError" || e.name === "NotFoundError");
      await say(denied ? "The microphone is blocked. Allow microphone access in your browser, then tap again." : asMessage(e));
    } finally { setPhase("idle"); setLevel(0); }
  }

  function toggle() {
    if (active) { stopSession(); return; }
    setPanelOpen(true);
    void session();
  }

  function stopSession() {
    stopped.current = true;
    recorder.current?.stop();
    stopSpeaking();
  }

  function closePanel() {
    if (active) stopSession();
    setPanelOpen(false);
  }

  function toggleReplies() {
    const next = !voiceReplies;
    setVoiceReplies(next); setRepliesEnabled(next);
    if (!next) stopSpeaking();
  }

  return (
    <aside aria-label="Voice assistant" className="fixed bottom-20 right-4 z-40 md:bottom-6 md:right-6">
      {panelOpen ? <section className="w-[min(21rem,calc(100vw-2rem))] overflow-hidden rounded-2xl border border-line bg-white shadow-hover" role="status" aria-live="polite">
        <header className="flex items-center justify-between border-b border-line bg-cream/70 px-3 py-2.5">
          <div className="flex min-w-0 items-center gap-2.5">
            <span className="grid h-9 w-9 shrink-0 place-items-center rounded-xl bg-brand-soft text-brand-dark">
              <span className={`voice-wave ${active ? "voice-wave-moving" : "voice-wave-idle"} ${phase === "listening" ? "voice-wave-listening" : ""}`} aria-hidden="true">
                {[0.3, 0.55, 0.85, 0.58, 1, 0.62, 0.9, 0.5, 0.34].map((weight, index) => {
                  const height = phase === "listening" ? 4 + Math.round(level * 18 * weight) : 4 + Math.round(weight * 10);
                  return <span key={index} className="voice-wave-bar" style={{ height, animationDelay: `${index * 65}ms` }} />;
                })}
              </span>
            </span>
            <span className="min-w-0"><strong className="block text-sm leading-tight">Gnani AI</strong><small className="block truncate text-[11px] text-stone-500">{LABEL[phase]}</small></span>
          </div>
          <button type="button" onClick={closePanel} className="grid h-8 w-8 shrink-0 place-items-center rounded-full text-xl leading-none text-stone-500 hover:bg-stone-100 hover:text-ink" aria-label="Close voice assistant" title="Close voice assistant">×</button>
        </header>
        <div className="space-y-2.5 p-3">
          {heard ? <p className="text-xs text-stone-500"><b className="mr-1.5 uppercase tracking-wide">You said</b>“{heard}”</p> : null}
          {reply ? <p className="rounded-xl bg-cream p-2.5 text-sm leading-snug">{reply}</p> : null}
          {!active && !heard && !reply ? <p className="text-xs leading-relaxed text-stone-500">Try “open orders”, “how many roses are left”, “give me a summary”, or “what can I say”.</p> : null}
          <div className="flex items-center justify-between gap-3 border-t border-line pt-2 text-[11px] text-stone-500">
            <button type="button" className="underline underline-offset-2" onClick={toggleReplies}>{voiceReplies ? "Mute spoken replies" : "Unmute spoken replies"}</button>
            <button type="button" className="underline underline-offset-2" onClick={() => setTyping(true)}>Type instead</button>
          </div>
          {!active ? <button type="button" onClick={() => void session()} className="flex w-full items-center justify-center gap-2 rounded-xl bg-brand px-3 py-2 text-sm font-bold text-brand-dark hover:bg-brand-hover"><Icon name="mic" size={16}/>Speak again</button> : null}
        </div>
      </section> : <button
        type="button"
        onClick={toggle}
        aria-pressed={false}
        aria-label="Open voice assistant and speak"
        title="Voice assistant · Tap and speak"
        className="grid h-14 w-14 place-items-center rounded-full border border-white/20 bg-ink text-brand shadow-hover transition-all duration-200 hover:scale-105 active:scale-95 focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-brand/40"
      ><Icon name="mic" className="h-5 w-5" /></button>}
      {typing ? <VoiceOrderModal onClose={() => setTyping(false)} onOrderCreated={() => window.dispatchEvent(new Event("factor:changed"))} /> : null}
    </aside>
  );
}
