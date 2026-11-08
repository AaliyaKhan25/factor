"use client";
import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { api, ApiError, Business, Me, tokenStore } from "./api";

type AuthState = {
  user: Me | null;
  business: Business | null;
  loading: boolean;
  hasActive: boolean;
  hasPending: boolean;
  isAdmin: boolean;
  login: (email: string, password: string) => Promise<void>;
  signup: (name: string, email: string, password: string) => Promise<void>;
  googleLogin: (credential: string) => Promise<void>;
  logout: () => void;
  refresh: () => Promise<void>;
};

const Ctx = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<Me | null>(null);
  const [business, setBusiness] = useState<Business | null>(null);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    if (!tokenStore.get()) {
      setUser(null);
      setBusiness(null);
      setLoading(false);
      return;
    }
    try {
      const me = await api<Me>("/auth/me");
      setUser(me);
      if (me.memberships.some((m) => m.status === "active")) {
        setBusiness(await api<Business>("/business"));
      } else {
        setBusiness(null);
      }
    } catch (e) {
      if (e instanceof ApiError && e.status === 401) tokenStore.clear();
      setUser(null);
      setBusiness(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const login = useCallback(
    async (email: string, password: string) => {
      const r = await api<{ access_token: string }>("/auth/login", {
        body: { email, password },
        auth: false,
      });
      tokenStore.set(r.access_token);
      setLoading(true);
      await refresh();
    },
    [refresh],
  );

  const signup = useCallback(
    async (name: string, email: string, password: string) => {
      await api("/auth/signup", { body: { name, email, password }, auth: false });
      await login(email, password);
    },
    [login],
  );

  const googleLogin = useCallback(
    async (credential: string) => {
      const r = await api<{ access_token: string }>("/auth/google", { body: { credential }, auth: false });
      tokenStore.set(r.access_token);
      setLoading(true);
      await refresh();
    },
    [refresh],
  );

  const logout = useCallback(() => {
    tokenStore.clear();
    setUser(null);
    setBusiness(null);
  }, []);

  const value = useMemo<AuthState>(() => {
    const ms = user?.memberships ?? [];
    return {
      user,
      business,
      loading,
      hasActive: ms.some((m) => m.status === "active"),
      hasPending: ms.some((m) => m.status === "pending"),
      isAdmin: business?.your_role === "admin",
      login,
      signup,
      googleLogin,
      logout,
      refresh,
    };
  }, [user, business, loading, login, signup, googleLogin, logout, refresh]);

  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useAuth(): AuthState {
  const v = useContext(Ctx);
  if (!v) throw new Error("useAuth must be used inside AuthProvider");
  return v;
}
