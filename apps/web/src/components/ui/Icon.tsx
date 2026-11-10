const PATHS: Record<string, string> = {
  home: "M3 11l9-8 9 8M5 10v10h5v-6h4v6h5V10",
  inbox: "M3 13l3-8h12l3 8M3 13v6h18v-6M3 13h5l1 3h6l1-3h5",
  box: "M21 8l-9-5-9 5 9 5 9-5zM3 8v8l9 5 9-5V8M12 13v8",
  tag: "M3 12V4h8l10 10-8 8L3 12zM8 8h.01",
  users: "M16 19v-1a4 4 0 00-4-4H7a4 4 0 00-4 4v1M9.5 10a3 3 0 100-6 3 3 0 000 6zM21 19v-1a4 4 0 00-3-3.9M16 4.1a3 3 0 010 5.8",
  team: "M12 12a4 4 0 100-8 4 4 0 000 8zM4 21a8 8 0 0116 0",
  gear: "M12 15a3 3 0 100-6 3 3 0 000 6zM19 12l2-1-2-4-2 1a7 7 0 00-2-1l-.5-2h-4L10 7a7 7 0 00-2 1L6 7 4 11l2 1a7 7 0 000 2l-2 1 2 4 2-1a7 7 0 002 1l.5 2h4L14 19a7 7 0 002-1l2 1 2-4-2-1a7 7 0 000-2z",
  plus: "M12 5v14M5 12h14",
  bell: "M6 8a6 6 0 1112 0c0 7 3 8 3 8H3s3-1 3-8M10 21h4",
  send: "M22 2L11 13M22 2l-7 20-4-9-9-4 20-7z",
  check: "M5 13l4 4L19 7",
  back: "M15 18l-6-6 6-6",
  spark: "M12 3l2 6 6 2-6 2-2 6-2-6-6-2 6-2 2-6z",
  wallet: "M3 7h16a2 2 0 012 2v9a2 2 0 01-2 2H5a2 2 0 01-2-2V7zm0 0V6a2 2 0 012-2h11M17 14h.01",
  truck: "M3 6h11v10H3zM14 9h4l3 3v4h-7M7 19a2 2 0 100-4 2 2 0 000 4zM17 19a2 2 0 100-4 2 2 0 000 4z",
  arrow: "M5 12h14M13 6l6 6-6 6",
  chart: "M3 3v18h18M18 17V9M13 17V5M8 17v-3",
  trending: "M23 6l-9.5 9.5-5-5L1 18M17 6h6v6",
  calendar: "M19 4H5a2 2 0 00-2 2v14a2 2 0 002 2h14a2 2 0 002-2V6a2 2 0 00-2-2zM16 2v4M8 2v4M3 10h18",
  refresh: "M23 4v6h-6M1 20v-6h6M3.51 9a9 9 0 0114.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0020.49 15",
  filter: "M22 3H2l8 9.46V19l4 2v-8.54L22 3z",
  target: "M12 22a10 10 0 100-20 10 10 0 000 20zM12 18a6 6 0 100-12 6 6 0 000 12zM12 14a2 2 0 100-4 2 2 0 000 4z",
  clock: "M12 22a10 10 0 100-20 10 10 0 000 20zM12 6v6l4 2",
  star: "M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z",
  zap: "M13 2L3 14h9l-1 8 10-12h-9l1-8z",
  info: "M12 22a10 10 0 100-20 10 10 0 000 20zM12 16v-4M12 8h.01",
  close: "M18 6L6 18M6 6l12 12",
  mic: "M12 1a3 3 0 00-3 3v8a3 3 0 006 0V4a3 3 0 00-3-3zM19 10v2a7 7 0 01-14 0v-2M12 19v4M8 23h8",
  waveform: "M3 10v4M7 6v12M11 3v18M15 7v10M19 10v4",
  search: "M11 19a8 8 0 110-16 8 8 0 010 16zM21 21l-4.35-4.35",
};

export default function Icon({
  name,
  className = "h-5 w-5",
  size,
}: {
  name: string;
  className?: string;
  size?: number;
}) {
  const style = size ? { width: size, height: size } : undefined;
  return (
    <svg
      style={style}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.8}
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
      aria-hidden="true"
    >
      <path d={PATHS[name] ?? PATHS.spark} />
    </svg>
  );
}
