"use client";
import { useCallback, useEffect, useRef, useState } from "react";

/** Load once, then keep refreshing. Pauses while the tab is hidden. */
export function usePolling<T>(load: () => Promise<T>, ms: number, key: string = "") {
  const loadRef = useRef(load);
  loadRef.current = load;
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const run = useCallback(async () => {
    try {
      const d = await loadRef.current();
      setData(d);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Something went wrong");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    let alive = true;
    setLoading(true);
    setData(null);
    run();
    const id = setInterval(() => {
      if (alive && document.visibilityState === "visible") run();
    }, ms);
    return () => {
      alive = false;
      clearInterval(id);
    };
  }, [run, ms, key]);

  return { data, error, loading, reload: run };
}
