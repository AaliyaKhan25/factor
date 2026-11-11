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
    if (active) { stopped.current = true; recorder.current?.stop(); stopSpeaking(); setPhase("idle"); return; }
    void session();
  }

  function toggleReplies() {
    const next = !voiceReplies;
    setVoiceReplies(next); setRepliesEnabled(next);
    if (!next) stopSpeaking();
  }

  return (
    <>
      <aside aria-label="Voice assistant" className="fixed bottom-20 right-4 z-40 flex max-w-[min(22rem,calc(100vw-2rem))] flex-col items-end gap-2 md:bottom-6 md:right-6">
        {(active || heard || reply) ? (
          <div className="w-full rounded-2xl border border-line bg-white p-3 text-sm shadow-hover" role="status" aria-live="polite">
            <p className="text-[10px] font-bold uppercase tracking-widest text-brand-dark">{LABEL[phase]}</p>
            {heard ? <p className="mt-1 text-xs text-stone-500">You: “{heard}”</p> : null}
            {reply ? <p className="mt-1 leading-snug">{reply}</p> : null}
            {!active ? <p className="mt-2 text-[11px] text-stone-500">Try: “open orders”, “how many roses are left”, “give me a summary”, “what can I say”.</p> : null}
            <div className="mt-2 flex items-center gap-3 text-[11px] text-stone-500">
              <button type="button" className="underline" onClick={toggleReplies}>{voiceReplies ? "Mute spoken replies" : "Unmute spoken replies"}</button>
              <button type="button" className="underline" onClick={() => setTyping(true)}>Type instead</button>
            </div>
          </div>
        ) : null}
        <button
          type="button"
          onClick={toggle}
          aria-pressed={active}
          aria-label={active ? "Stop voice assistant" : "Start voice assistant"}
          title="Voice assistant. Tap, then speak."
          className="group flex items-center gap-2.5 rounded-full border border-white/10 bg-ink px-4 py-3 text-white shadow-hover transition-all duration-300 hover:scale-105 active:scale-95"
        >
          <span className="relative grid h-9 w-9 place-items-center rounded-full bg-brand text-brand-dark shadow-glow">
            <span className={`absolute rounded-full bg-brand/40 ${phase === "listening" ? "animate-ping" : ""}`} style={{ inset: `${-4 - Math.round(level * 8)}px` }} />
            <Icon name="mic" className="relative z-10 h-4 w-4" />
          </span>
          <span className="text-left">
            <span className="block text-xs font-bold leading-tight">{active ? LABEL[phase] : "Voice"}</span>
            <span className="block text-[10px] font-medium text-brand">{active ? "Tap to stop" : "Tap and speak"}</span>
          </span>
        </button>
      </aside>
      {typing ? <VoiceOrderModal onClose={() => setTyping(false)} onOrderCreated={() => window.dispatchEvent(new Event("factor:changed"))} /> : null}
    </>
  );
}