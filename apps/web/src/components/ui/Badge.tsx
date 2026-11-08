const tones = {
  green: "bg-emerald-100 text-emerald-800",
  lime: "bg-brand-soft text-brand-dark",
  amber: "bg-amber-100 text-amber-800",
  red: "bg-red-100 text-red-800",
  blue: "bg-sky-100 text-sky-800",
  gray: "bg-stone-200 text-stone-700",
} as const;

export type Tone = keyof typeof tones;

export default function Badge({ tone = "gray", children }: { tone?: Tone; children: React.ReactNode }) {
  return <span className={`inline-block whitespace-nowrap rounded-full px-2.5 py-0.5 text-xs font-semibold ${tones[tone]}`}>{children}</span>;
}
