"use client";

// Spoken output for the whole app. Gnani text to speech goes through the API (the key never reaches the browser).
// If that is unavailable (signed out, offline, no key), the browser's own voice is used so errors are still heard.
import { API_URL, tokenStore } from "./api";

const KEY = "factor_voice_replies";
let current: HTMLAudioElement | null = null;

export function repliesEnabled(): boolean {
  try { return localStorage.getItem(KEY) !== "0"; } catch { return true; }
}

export function setRepliesEnabled(on: boolean) {
  try { localStorage.setItem(KEY, on ? "1" : "0"); } catch { /* storage unavailable */ }
}

export function stopSpeaking() {
  try { current?.pause(); } catch { /* ignore */ }
  current = null;
  if (typeof window !== "undefined") window.speechSynthesis?.cancel();
}

function browserSpeak(text: string): Promise<void> {
  return new Promise((resolve) => {
    if (typeof window === "undefined" || !("speechSynthesis" in window)) return resolve();
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.lang = "en-IN";
    utterance.onend = () => resolve();
    utterance.onerror = () => resolve();
    window.speechSynthesis.speak(utterance);
  });
}

function play(base64: string): Promise<void> {
  return new Promise((resolve, reject) => {
    const audio = new Audio(`data:audio/wav;base64,${base64}`);
    current = audio;
    audio.onended = () => resolve();
    audio.onerror = () => reject(new Error("audio playback failed"));
    audio.play().catch(reject);
  });
}

/** Speak text and resolve when it has finished. Never throws. */
export async function speak(text: string, audioBase64?: string): Promise<void> {
  const clean = text.trim();
  if (!clean) return;
  stopSpeaking();
  try {
    if (audioBase64) { await play(audioBase64); return; }
    if (tokenStore.get()) {
      const res = await fetch(`${API_URL}/voice/speak`, {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${tokenStore.get()}` },
        body: JSON.stringify({ text: clean.slice(0, 590) }),
      });
      if (res.ok) { const data = await res.json(); await play(data.audio_base64); return; }
    }
  } catch { /* fall through to the browser voice */ }
  await browserSpeak(clean);
}