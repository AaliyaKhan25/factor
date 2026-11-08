export default function ChannelBadge({ channel }: { channel: string }) {
  const ig = channel === "instagram";
  const wa = channel === "whatsapp";
  const voice = channel === "voice";
  return (
    <span
      className={`inline-flex items-center gap-1 rounded-md px-1.5 py-0.5 text-[10px] font-bold uppercase tracking-wide ${
        voice
          ? "bg-brand-soft text-brand-dark border border-brand/60"
          : ig
          ? "bg-pink-100 text-pink-700"
          : wa
          ? "bg-emerald-100 text-emerald-700"
          : "bg-stone-200 text-stone-600"
      }`}
    >
      {voice ? "🎙 Voice (Gnani)" : ig ? "Instagram" : wa ? "WhatsApp" : "Manual"}
    </span>
  );
}
