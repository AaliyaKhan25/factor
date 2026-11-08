"use client";
import { useEffect } from "react";
import { usePathname, useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth";
import AppShell from "@/components/layout/AppShell";

export default function AppLayout({ children }: { children: React.ReactNode }) {
  const { user, loading, hasActive } = useAuth();
  const router = useRouter();
  const path = usePathname();

  useEffect(() => {
    if (loading) return;
    if (!user) router.replace("/login");
    else if (!hasActive && path !== "/onboarding") router.replace("/onboarding");
    else if (hasActive && path === "/onboarding") router.replace("/dashboard");
  }, [loading, user, hasActive, path, router]);

  if (loading || !user) return <p className="p-6 text-stone-500">Loading…</p>;
  if (!hasActive) return path === "/onboarding" ? <>{children}</> : null;
  return <AppShell>{children}</AppShell>;
}
