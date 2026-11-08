"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import Modal from "@/components/ui/Modal";
import Button from "@/components/ui/Button";
import Icon from "@/components/ui/Icon";
import { rupees } from "@/lib/format";
import { submitVoiceOrder, SpeechListener, AudioRecorder } from "@/lib/voice";
import { VoiceOrderResult } from "@/lib/api";

const PRESET_VOICE_COMMANDS = [
  "rahul bought 80 roses , total price 1600",
  "ananya ordered 2 pearl chokers, total price 17800",
  "rahul ne 80 roses khareede, total 1600 rupaye",
  "sneha phone 9876543210 bought 4 scrunchies for 800",
];

const LANGUAGES = [
  { code: "en-IN", label: "Indian English" },
  { code: "hi-IN", label: "Hindi (हिंदी)" },
  { code: "gu-IN", label: "Gujarati (ગુજરાતી)" },
  { code: "mr-IN", label: "Marathi (मराठी)" },
  { code: "kn-IN", label: "Kannada (ಕನ್ನಡ)" },
  { code: "ta-IN", label: "Tamil (தமிழ்)" },
  { code: "te-IN", label: "Telugu (తెలుగు)" },
];

interface Props {
  onClose: () => void;
  onOrderCreated?: (order: VoiceOrderResult["order"]) => void;
}

export default function VoiceOrderModal({ onClose, onOrderCreated }: Props) {
  const router = useRouter();
  const [isListening, setIsListening] = useState(false);
  const [transcript, setTranscript] = useState("");
  const [language, setLanguage] = useState("en-IN");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [createdOrder, setCreatedOrder] = useState<VoiceOrderResult | null>(null);

  const listenerRef = useRef<SpeechListener | null>(null);
  const recorderRef = useRef<AudioRecorder | null>(null);

  // Initialize Speech Listener
  useEffect(() => {
    listenerRef.current = new SpeechListener(
      (text) => {
        setTranscript(text);
        setError(null);
      },
      (err) => {
        setError(`Microphone: ${err}`);
        setIsListening(false);
      },
      () => {
        setIsListening(false);
      },
      language
    );

    return () => {
      listenerRef.current?.stop();
    };
  }, [language]);

  const toggleListening = async () => {
    if (isListening) {
      listenerRef.current?.stop();
      setIsListening(false);
    } else {
      setError(null);
      setTranscript("");
      setCreatedOrder(null);
      setIsListening(true);
      listenerRef.current?.start();
    }
  };

  const handleProcessOrder = async (textToProcess?: string) => {
    const text = (textToProcess ?? transcript).trim();
    if (!text) {
      setError("Please speak into the mic or select a sample voice command first.");
      return;
    }

    if (isListening) {
      listenerRef.current?.stop();
      setIsListening(false);
    }

    setBusy(true);
    setError(null);

    try {
      const result = await submitVoiceOrder(text, language);
      setCreatedOrder(result);
      onOrderCreated?.(result.order);
    } catch (err: any) {
      setError(err?.message || "Could not process voice order. Check backend connection.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <Modal title="Gnani.ai Voice Order Assistant" onClose={onClose}>
      <div className="space-y-4">
        {/* Banner with Gnani.ai attribution and status */}
        <div className="flex items-center justify-between rounded-xl bg-brand-soft/70 px-3.5 py-2.5 text-xs text-brand-dark">
          <div className="flex items-center gap-2">
            <span className="grid h-6 w-6 place-items-center rounded-lg bg-brand text-brand-dark shadow-xs">
              <Icon name="mic" className="h-3.5 w-3.5" />
            </span>
            <span className="font-bold">Powered by Gnani.ai Indic Voice AI</span>
          </div>
          <span className="flex items-center gap-1 font-semibold">
            <span className="h-2 w-2 rounded-full bg-brand-dark animate-pulse" />
            Live Assistant
          </span>
        </div>

        {/* Success View */}
        {createdOrder ? (
          <div className="space-y-4 rounded-2xl border border-brand/60 bg-white p-5 shadow-card animate-fadeIn">
            <div className="flex items-center gap-3">
              <span className="grid h-12 w-12 place-items-center rounded-2xl bg-brand text-brand-dark shadow-sm">
                <Icon name="check" className="h-6 w-6" />
              </span>
              <div>
                <span className="rounded-full bg-brand-soft px-2 py-0.5 text-[10px] font-bold text-brand-dark">
                  Order Automatically Created!
                </span>
                <h3 className="font-display text-xl font-bold text-ink">
                  {createdOrder.order.code} · {createdOrder.order.customer_name}
                </h3>
              </div>
            </div>

            <div className="rounded-xl bg-cream/60 p-3.5 space-y-2 text-xs">
              <p className="font-semibold text-stone-500">Extracted from Voice:</p>
              <p className="font-medium italic text-ink">"{createdOrder.transcript}"</p>
              <div className="border-t border-line/60 pt-2 flex items-center justify-between font-bold text-ink">
                <span>Total Amount:</span>
                <span className="font-display text-base text-brand-dark">{rupees(createdOrder.order.total_paise)}</span>
              </div>
            </div>

            <div className="flex gap-2">
              <Button
                variant="primary"
                className="flex-1"
                onClick={() => {
                  onClose();
                  router.push(`/orders/${createdOrder.order.id}`);
                }}
              >
                View Created Order
              </Button>
              <Button
                variant="secondary"
                onClick={() => {
                  setCreatedOrder(null);
                  setTranscript("");
                }}
              >
                New Voice Note
              </Button>
            </div>
          </div>
        ) : (
          <>
            {/* Language Selector */}
            <div className="flex items-center justify-between text-xs">
              <label className="font-semibold text-stone-600">Spoken Language:</label>
              <select
                value={language}
                onChange={(e) => setLanguage(e.target.value)}
                className="rounded-lg border border-line bg-white px-2.5 py-1 text-xs font-semibold focus:border-brand-dark focus:outline-none"
              >
                {LANGUAGES.map((l) => (
                  <option key={l.code} value={l.code}>
                    {l.label}
                  </option>
                ))}
              </select>
            </div>

            {/* Central Animated Mic Pulse Button */}
            <div className="flex flex-col items-center justify-center rounded-2xl border border-line bg-cream/40 p-6 text-center">
              <button
                type="button"
                onClick={toggleListening}
                className={`relative grid h-20 w-20 place-items-center rounded-full transition-all duration-300 shadow-md ${
                  isListening
                    ? "bg-red-500 text-white ring-8 ring-red-200 animate-pulse"
                    : "bg-brand text-brand-dark hover:bg-brand-hover hover:scale-105 active:scale-95 shadow-glow"
                }`}
                title={isListening ? "Stop listening" : "Start speaking"}
              >
                <Icon name="mic" className="h-8 w-8" />
              </button>

              <p className="mt-3 text-sm font-bold text-ink">
                {isListening ? "Listening... Speak your order naturally" : "Tap the mic and speak"}
              </p>
              <p className="mt-0.5 text-xs text-stone-500 max-w-xs">
                Say e.g. "Rahul bought 80 roses, total price 1600"
              </p>

              {/* Soundwave Animation while listening */}
              {isListening && (
                <div className="mt-4 flex items-center gap-1.5 h-6">
                  {[40, 75, 100, 60, 90, 45, 80, 50, 95, 30].map((h, i) => (
                    <span
                      key={i}
                      className="w-1 rounded-full bg-brand-dark animate-pulse"
                      style={{
                        height: `${h}%`,
                        animationDelay: `${i * 0.1}s`,
                      }}
                    />
                  ))}
                </div>
              )}
            </div>

            {/* Transcript Display & Text Input */}
            <div>
              <div className="flex items-center justify-between mb-1">
                <span className="text-xs font-semibold text-stone-600">Voice Transcript:</span>
                {transcript && (
                  <button
                    type="button"
                    onClick={() => setTranscript("")}
                    className="text-[10px] text-stone-400 hover:text-ink"
                  >
                    Clear
                  </button>
                )}
              </div>
              <textarea
                rows={2}
                value={transcript}
                onChange={(e) => setTranscript(e.target.value)}
                placeholder="Spoken words will appear here in real-time, or type directly..."
                className="w-full rounded-xl border border-line bg-white p-3 text-xs leading-relaxed placeholder:text-stone-400 focus:border-brand-dark focus:outline-none"
              />
            </div>

            {/* Quick Preset Voice Orders */}
            <div>
              <span className="mb-1.5 block text-[11px] font-bold uppercase tracking-wider text-stone-500">
                Quick Test Prompts (Tap to test):
              </span>
              <div className="flex flex-wrap gap-1.5">
                {PRESET_VOICE_COMMANDS.map((cmd) => (
                  <button
                    key={cmd}
                    type="button"
                    onClick={() => {
                      setTranscript(cmd);
                      handleProcessOrder(cmd);
                    }}
                    className="rounded-lg border border-line bg-white px-2.5 py-1 text-[11px] font-medium text-stone-700 transition-colors hover:border-brand hover:bg-brand-soft hover:text-brand-dark text-left"
                  >
                    "{cmd}"
                  </button>
                ))}
              </div>
            </div>

            {/* Error Message */}
            {error && (
              <div className="rounded-xl bg-red-50 p-3 text-xs font-medium text-red-700 border border-red-200">
                {error}
              </div>
            )}

            {/* Submit Action */}
            <Button
              type="button"
              disabled={busy || !transcript.trim()}
              onClick={() => handleProcessOrder()}
              className="w-full min-h-11 font-bold"
            >
              {busy ? "Booking order via Gnani.ai…" : "Create Order from Voice"}
            </Button>
          </>
        )}
      </div>
    </Modal>
  );
}
