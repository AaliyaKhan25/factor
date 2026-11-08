export default function Brand({ size = "md" }: { size?: "md" | "lg" }) {
  const box = size === "lg" ? "h-11 w-11 text-2xl" : "h-9 w-9 text-xl";
  return (
    <div className="flex items-center gap-2.5">
      <span className={`grid ${box} place-items-center rounded-xl bg-brand font-serif font-bold text-brand-dark`}>f</span>
      <span className={`font-serif font-bold tracking-tight ${size === "lg" ? "text-3xl" : "text-2xl"}`}>factor<span className="text-brand-dark">.</span></span>
    </div>
  );
}
