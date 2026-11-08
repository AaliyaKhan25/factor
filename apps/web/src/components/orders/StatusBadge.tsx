import Badge, { Tone } from "@/components/ui/Badge";

const TONES: Record<string, Tone> = { new: "blue", confirmed: "lime", packed: "lime", shipped: "amber", delivered: "green", cancelled: "gray" };

export default function StatusBadge({ status }: { status: string }) {
  return <Badge tone={TONES[status] ?? "gray"}>{status}</Badge>;
}
