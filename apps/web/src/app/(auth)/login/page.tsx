"use client";
import Link from "next/link";
import { FormEvent, useCallback, useState } from "react";
import { useAuth } from "@/lib/auth";
import AuthFrame from "@/components/auth/AuthFrame";
import GoogleButton from "@/components/auth/GoogleButton";
import Button from "@/components/ui/Button";
import Input from "@/components/ui/Input";
import ErrorText from "@/components/ui/ErrorText";

export default function LoginPage() {
  const { login } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const onGoogleError = useCallback((m: string) => setError(m), []);

  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await login(email, password);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong");
      setBusy(false);
    }
  }

  return (
    <AuthFrame title="Welcome back" subtitle="Sign in to see what your customers are asking.">
      <div className="mt-6 space-y-4">
        <GoogleButton onError={onGoogleError} />
        <div className="flex items-center gap-3 text-xs text-stone-400"><span className="h-px flex-1 bg-line" />or with email<span className="h-px flex-1 bg-line" /></div>
      </div>
      <form onSubmit={submit} className="mt-4 space-y-4">
        <Input label="Email" type="email" autoComplete="email" required value={email} onChange={(e) => setEmail(e.target.value)} />
        <Input label="Password" type="password" autoComplete="current-password" required value={password} onChange={(e) => setPassword(e.target.value)} />
        <ErrorText message={error} />
        <Button type="submit" disabled={busy} className="w-full">{busy ? "Please wait…" : "Sign in"}</Button>
      </form>
      <p className="mt-6 text-center text-sm text-stone-600">
        New here? <Link href="/signup" className="font-semibold text-brand-dark underline">Create an account</Link>
      </p>
    </AuthFrame>
  );
}
