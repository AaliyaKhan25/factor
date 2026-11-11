"use client";

import { useEffect } from "react";
import { repliesEnabled, speak } from "@/lib/speak";

/** Reads every API error aloud, on every screen. The same message is not repeated within 30 seconds. */
export default function VoiceErrors() {
  useEffect(() => {
    const recent = new Map<string, number>();
    function onError(event: Event) {
      const message = (event as CustomEvent<{ message: string }>).detail?.message;
      if (!message || !repliesEnabled()) return;
      const now = Date.now();
      if (now - (recent.get(message) ?? 0) < 30_000) return;
      recent.set(message, now);
      void speak(message);
    }
    window.addEventListener("factor:error", onError);
    return () => window.removeEventListener("factor:error", onError);
  }, []);
  return null;
}