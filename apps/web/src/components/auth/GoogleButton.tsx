"use client";
import { useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";

declare global {
  interface Window {
    google?: any; // eslint-disable-line @typescript-eslint/no-explicit-any
  }
}

export default function GoogleButton({ onError }: { onError: (m: string) => void }) {
  const { googleLogin } = useAuth();
  const box = useRef<HTMLDivElement>(null);
  const [clientId, setClientId] = useState<string | null | undefined>(undefined);

  useEffect(() => {
    api<{ google_client_id: string | null }>("/auth/config", { auth: false })
      .then((c) => setClientId(c.google_client_id))
      .catch(() => setClientId(null));
  }, []);

  useEffect(() => {
    if (!clientId) return;
    const start = () => {
      if (!window.google || !box.current) return;
      window.google.accounts.id.initialize({
        client_id: clientId,
        callback: (r: { credential: string }) => googleLogin(r.credential).catch((e: Error) => onError(e.message)),
      });
      window.google.accounts.id.renderButton(box.current, { theme: "outline", size: "large", width: 320, text: "continue_with" });
    };
    if (window.google) return start();
    const s = document.createElement("script");
    s.src = "https://accounts.google.com/gsi/client";
    s.async = true;
    s.onload = start;
    document.head.appendChild(s);
  }, [clientId, googleLogin, onError]);

  if (clientId === undefined) return null;
  if (!clientId) {
    return process.env.NODE_ENV !== "production" ? (
      <p className="rounded-lg bg-stone-100 px-3 py-2 text-center text-xs text-stone-500">
        Google sign-in is off. Set GOOGLE_CLIENT_ID on the API to turn it on.
      </p>
    ) : null;
  }
  return <div ref={box} className="flex justify-center" />;
}
