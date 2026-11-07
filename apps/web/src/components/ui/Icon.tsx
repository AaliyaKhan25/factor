import type { SVGProps } from "react";

const paths: Record<string, string> = {
  grid: "M3 3h7v7H3zM14 3h7v7h-7zM14 14h7v7h-7zM3 14h7v7H3z",
  inbox: "M4 4h16v13h-5l-2 3h-2l-2-3H4zM4 13h4l2 3h4l2-3h4",
  box: "M4 7 12 3l8 4v10l-8 4-8-4zM4 7l8 4 8-4M12 11v10M8 5l8 4",
  calendar: "M4 5h16v16H4zM8 3v4M16 3v4M4 10h16",
  wallet: "M3 6h17a1 1 0 0 1 1 1v12H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h14M16 13h5M5 7v12",
  users: "M16 21v-2a4 4 0 0 0-4-4H7a4 4 0 0 0-4 4v2M9.5 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8M17 11a4 4 0 0 0 0-8M21 21v-2a4 4 0 0 0-3-3.87",
  chart: "M3 3v18h18M8 16V9M13 16V5M18 16v-7",
  settings: "M12 8a4 4 0 1 0 0 8 4 4 0 0 0 0-8M19.4 15a1.7 1.7 0 0 0 .3 1.9l.1.1-1.8 3.1-.2-.1a1.7 1.7 0 0 0-1.9.3l-.1.1h-3.6l-.1-.2a1.7 1.7 0 0 0-1.6-1.2 1.7 1.7 0 0 0-1.6 1.2l-.1.2H5.2l-.1-.2a1.7 1.7 0 0 0-1.9-.3l-.2.1-1.8-3.1.1-.1a1.7 1.7 0 0 0 .3-1.9l-.1-.2v-3.6l.2-.1a1.7 1.7 0 0 0 1.2-1.6 1.7 1.7 0 0 0-1.2-1.6l-.2-.1V4.2l.2-.1a1.7 1.7 0 0 0 .3-1.9l-.1-.2 3.1-1.8.1.1a1.7 1.7 0 0 0 1.9.3l.2-.1h3.6l.1.2a1.7 1.7 0 0 0 1.6 1.2 1.7 1.7 0 0 0 1.6-1.2l.1-.2h3.6l.1.2a1.7 1.7 0 0 0 1.9.3l.2-.1 1.8 3.1-.1.1a1.7 1.7 0 0 0-.3 1.9l.1.2v3.6l-.2.1a1.7 1.7 0 0 0-1.2 1.6 1.7 1.7 0 0 0 1.2 1.6l.2.1v3.6z",
  search: "m20 20-4-4M17 10a7 7 0 1 1-14 0 7 7 0 0 1 14 0Z",
  plus: "M12 5v14M5 12h14",
  arrow: "M5 12h14M13 6l6 6-6 6",
  clock: "M12 8v4l3 2M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z",
  check: "m5 12 4 4L19 6",
  chevron: "m9 18 6-6-6-6",
  mic: "M12 18v4M8 22h8M19 10v2a7 7 0 0 1-14 0v-2M12 15a3 3 0 0 0 3-3V5a3 3 0 0 0-6 0v7a3 3 0 0 0 3 3Z",
  bell: "M18 8a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9M10 21h4",
  menu: "M4 6h16M4 12h16M4 18h16",
  close: "M18 6 6 18M6 6l12 12",
  filter: "M4 5h16M7 12h10M10 19h4",
  trend: "m3 17 6-6 4 4 8-8M15 7h6v6",
  package: "m12 3 9 5-9 5-9-5 9-5ZM3 8v9l9 5 9-5V8M12 13v9",
  pin: "M20 10c0 5-8 11-8 11S4 15 4 10a8 8 0 1 1 16 0ZM12 10a2 2 0 1 0 0-4 2 2 0 0 0 0 4Z",
  spark: "m12 3 1.8 5.2L19 10l-5.2 1.8L12 17l-1.8-5.2L5 10l5.2-1.8L12 3ZM19 16l1 2.5 2.5 1-2.5 1-1 2.5-1-2.5-2.5-1 2.5-1 1-2.5Z",
};

export type IconName = keyof typeof paths;

export default function Icon({ name, size = 20, ...props }: SVGProps<SVGSVGElement> & { name: IconName; size?: number }) {
  return <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" {...props}><path d={paths[name]} /></svg>;
}
