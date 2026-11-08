export default function ChannelBadge({ channel }: { channel: string }) {
  const ig = channel === "instagram";
  return (
    <span className={`inline-block rounded-md px-1.5 py-0.5 text-[11px] font-bold uppercase tracking-wide ${ig ? "bg-pink-100 text-pink-700" : channel === "whatsapp" ? "bg-emerald-100 text-emerald-700" : "bg-stone-200 text-stone-600"}`}>
      {ig ? "Instagram" : channel === "whatsapp" ? "WhatsApp" : "Manual"}
    </span>
  );
}
