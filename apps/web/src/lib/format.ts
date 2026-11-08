export function rupees(paise: number): string {
  const whole = paise % 100 === 0;
  return (
    "₹" +
    (paise / 100).toLocaleString("en-IN", {
      minimumFractionDigits: whole ? 0 : 2,
      maximumFractionDigits: 2,
    })
  );
}

/** The API sends UTC times without a zone marker. */
export function parseTime(iso: string): Date {
  return new Date(/[zZ]|[+-]\d\d:?\d\d$/.test(iso) ? iso : iso + "Z");
}

export function timeAgo(iso: string): string {
  const s = Math.max(0, (Date.now() - parseTime(iso).getTime()) / 1000);
  if (s < 60) return "just now";
  if (s < 3600) return `${Math.floor(s / 60)} min ago`;
  if (s < 86400) return `${Math.floor(s / 3600)} h ago`;
  if (s < 86400 * 7) return `${Math.floor(s / 86400)} d ago`;
  return parseTime(iso).toLocaleDateString("en-IN", { day: "numeric", month: "short" });
}

export function clock(iso: string): string {
  return parseTime(iso).toLocaleTimeString("en-IN", { hour: "numeric", minute: "2-digit" });
}

export function initials(name: string): string {
  return (
    name
      .replace(/[^\p{L}\p{N} ]/gu, " ")
      .split(" ")
      .filter(Boolean)
      .slice(0, 2)
      .map((p) => p[0].toUpperCase())
      .join("") || "?"
  );
}
