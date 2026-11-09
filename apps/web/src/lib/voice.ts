"use client";

import { RecordingStateMachine } from "./voice-state.mjs";
export { RecordingStateMachine };

export type RecordingResult = { blob: Blob; reason: "silence" | "limit" | "manual" };

function wav(samples: Float32Array, inputRate: number): Blob {
  const outputRate = 16000;
  const ratio = inputRate / outputRate;
  const length = Math.ceil(samples.length / ratio);
  const buffer = new ArrayBuffer(44 + length * 2);
  const view = new DataView(buffer);
  const write = (offset: number, value: string) => [...value].forEach((c, i) => view.setUint8(offset + i, c.charCodeAt(0)));
  write(0, "RIFF"); view.setUint32(4, 36 + length * 2, true); write(8, "WAVE"); write(12, "fmt ");
  view.setUint32(16, 16, true); view.setUint16(20, 1, true); view.setUint16(22, 1, true);
  view.setUint32(24, outputRate, true); view.setUint32(28, outputRate * 2, true); view.setUint16(32, 2, true);
  view.setUint16(34, 16, true); write(36, "data"); view.setUint32(40, length * 2, true);
  for (let i = 0; i < length; i++) {
    const sample = Math.max(-1, Math.min(1, samples[Math.floor(i * ratio)] ?? 0));
    view.setInt16(44 + i * 2, sample < 0 ? sample * 32768 : sample * 32767, true);
  }
  return new Blob([buffer], { type: "audio/wav" });
}

export class AudioRecorder {
  private context?: AudioContext;
  private stream?: MediaStream;
  private processor?: ScriptProcessorNode;
  private chunks: Float32Array[] = [];
  private timer?: number;
  private machine = new RecordingStateMachine();
  private done?: (result: RecordingResult) => void;
  private finished = false;

  async start(onLevel?: (level: number) => void): Promise<RecordingResult> {
    this.stream = await navigator.mediaDevices.getUserMedia({ audio: { channelCount: 1, echoCancellation: true, noiseSuppression: true } });
    this.context = new AudioContext();
    const source = this.context.createMediaStreamSource(this.stream);
    this.processor = this.context.createScriptProcessor(2048, 1, 1);
    const silentOutput = this.context.createGain(); silentOutput.gain.value = 0;
    source.connect(this.processor); this.processor.connect(silentOutput); silentOutput.connect(this.context.destination);
    this.processor.onaudioprocess = (event) => {
      const samples = new Float32Array(event.inputBuffer.getChannelData(0));
      this.chunks.push(samples);
      let energy = 0; for (const sample of samples) energy += sample * sample;
      onLevel?.(Math.min(1, Math.sqrt(energy / samples.length) * 7));
    };
    return new Promise((resolve) => {
      this.done = resolve;
      let previous = performance.now();
      this.timer = window.setInterval(() => {
        const now = performance.now(); const delta = Math.min(150, now - previous); previous = now;
        const samples = this.chunks[this.chunks.length - 1];
        let rms = 0;
        if (samples?.length) { let sum = 0; for (const sample of samples) sum += sample * sample; rms = Math.sqrt(sum / samples.length); }
        const state = this.machine.update(rms, delta);
        if (state !== "continue") this.finish(state);
      }, 100);
    });
  }

  stop() { this.finish("manual"); }

  private finish(reason: RecordingResult["reason"]) {
    if (this.finished) return; this.finished = true;
    if (this.timer) window.clearInterval(this.timer);
    if (this.processor) { this.processor.disconnect(); this.processor.onaudioprocess = null; }
    // A browser track's early `ended` event is intentionally ignored; only silence, cap, or a user tap finishes.
    this.stream?.getTracks().forEach((track) => track.stop());
    const inputRate = this.context?.sampleRate ?? 48000;
    void this.context?.close();
    const all = new Float32Array(this.chunks.reduce((n, part) => n + part.length, 0));
    let offset = 0; for (const part of this.chunks) { all.set(part, offset); offset += part.length; }
    this.done?.({ blob: wav(all, inputRate), reason });
  }
}

export async function postVoiceAudio(blob: Blob) {
  return sendAudio(blob, "/voice/transcribe-and-command");
}

export async function postVoiceConfirmation(blob: Blob, token: string) {
  return sendAudio(blob, `/voice/proposals/${token}/confirm-audio`);
}

async function sendAudio(blob: Blob, path: string) {
  const bytes = new Uint8Array(await blob.arrayBuffer());
  let binary = ""; for (const byte of bytes) binary += String.fromCharCode(byte);
  const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"}${path}`, {
    method: "POST", headers: { "Content-Type": "application/json", ...authHeader() },
    body: JSON.stringify({ audio_base64: btoa(binary), content_type: "audio/wav", language: "indic-auto" }),
  });
  const result = await response.json();
  if (!response.ok) throw new Error(result?.detail ?? "Voice command failed");
  return result;
}

function authHeader(): Record<string, string> {
  try { const token = localStorage.getItem("factor_token"); return token ? { Authorization: `Bearer ${token}` } : {}; }
  catch { return {}; }
}
