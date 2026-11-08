"use client";

import { api, VoiceOrderResult } from "./api";

/** Check if Web Speech Recognition is supported in this browser */
export function isSpeechRecognitionSupported(): boolean {
  if (typeof window === "undefined") return false;
  return "SpeechRecognition" in window || "webkitSpeechRecognition" in window;
}

/** Submit transcribed natural language order to Gnani.ai backend parsing service */
export async function submitVoiceOrder(
  text: string,
  language: string = "en-IN"
): Promise<VoiceOrderResult> {
  return await api<VoiceOrderResult>("/voice/parse-order", {
    method: "POST",
    body: { text, language },
  });
}

/** Submit base64 encoded audio from mic directly to Gnani.ai ASR backend */
export async function submitAudioVoiceOrder(
  audioBase64: string,
  contentType: string = "audio/wav",
  language: string = "en-IN"
): Promise<VoiceOrderResult> {
  return await api<VoiceOrderResult>("/voice/transcribe-and-order", {
    method: "POST",
    body: {
      audio_base64: audioBase64,
      content_type: contentType,
      language,
    },
  });
}

/** Record microphone audio using browser MediaRecorder and return base64 string */
export class AudioRecorder {
  private mediaRecorder: MediaRecorder | null = null;
  private audioChunks: Blob[] = [];

  async start(): Promise<void> {
    this.audioChunks = [];
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    this.mediaRecorder = new MediaRecorder(stream);

    this.mediaRecorder.ondataavailable = (event) => {
      if (event.data.size > 0) {
        this.audioChunks.push(event.data);
      }
    };

    this.mediaRecorder.start();
  }

  async stop(): Promise<{ blob: Blob; base64: string }> {
    return new Promise((resolve, reject) => {
      if (!this.mediaRecorder) {
        return reject(new Error("MediaRecorder not started"));
      }

      this.mediaRecorder.onstop = () => {
        const audioBlob = new Blob(this.audioChunks, { type: "audio/wav" });
        const reader = new FileReader();
        reader.onloadend = () => {
          const result = reader.result as string;
          const base64Data = result.split(",")[1] || result;
          // Stop all mic tracks
          this.mediaRecorder?.stream.getTracks().forEach((track) => track.stop());
          resolve({ blob: audioBlob, base64: base64Data });
        };
        reader.onerror = reject;
        reader.readAsDataURL(audioBlob);
      };

      this.mediaRecorder.stop();
    });
  }
}

/** Real-time Speech Recognition Controller */
export class SpeechListener {
  private recognition: any = null;
  public isListening = false;

  constructor(
    private onResult: (text: string, isFinal: boolean) => void,
    private onError: (err: string) => void,
    private onEnd: () => void,
    private language: string = "en-IN"
  ) {
    if (typeof window !== "undefined") {
      const SpeechRec =
        (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
      if (SpeechRec) {
        this.recognition = new SpeechRec();
        this.recognition.continuous = true;
        this.recognition.interimResults = true;
        this.recognition.lang = language;

        this.recognition.onresult = (event: any) => {
          let interimTranscript = "";
          let finalTranscript = "";

          for (let i = event.resultIndex; i < event.results.length; ++i) {
            const transcript = event.results[i][0].transcript;
            if (event.results[i].isFinal) {
              finalTranscript += transcript;
            } else {
              interimTranscript += transcript;
            }
          }

          const currentText = (finalTranscript || interimTranscript).trim();
          if (currentText) {
            this.onResult(currentText, Boolean(finalTranscript));
          }
        };

        this.recognition.onerror = (event: any) => {
          this.isListening = false;
          this.onError(event.error || "Speech recognition error");
        };

        this.recognition.onend = () => {
          this.isListening = false;
          this.onEnd();
        };
      }
    }
  }

  start() {
    if (!this.recognition) {
      this.onError("Speech recognition not supported in this browser. You can type or use sample audio.");
      return;
    }
    try {
      this.isListening = true;
      this.recognition.start();
    } catch (e: any) {
      this.isListening = false;
      this.onError(e.message || "Could not start microphone");
    }
  }

  stop() {
    if (this.recognition && this.isListening) {
      this.isListening = false;
      try {
        this.recognition.stop();
      } catch {
        /* already stopped */
      }
    }
  }
}
