"use client";

import { useState } from "react";
import Icon from "@/components/ui/Icon";
import VoiceOrderModal from "./VoiceOrderModal";

export default function FloatingVoiceButton() {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <>
      {/* Floating Action Button */}
      <aside aria-label="Voice Order Assistant" className="fixed bottom-6 right-6 z-40 hidden sm:block">
        <button
          onClick={() => setIsOpen(true)}
          className="group flex items-center gap-2.5 rounded-full bg-ink px-4 py-3 text-white shadow-hover transition-all duration-300 hover:scale-105 hover:bg-black active:scale-95 border border-white/10"
          title="Voice-based order with Gnani.ai"
        >
          <span className="relative grid h-8 w-8 place-items-center rounded-full bg-brand text-brand-dark shadow-glow">
            <span className="absolute -inset-1 rounded-full bg-brand/40 animate-ping opacity-75" />
            <Icon name="mic" className="h-4 w-4 relative z-10" />
          </span>
          <div className="text-left">
            <span className="block text-xs font-bold leading-tight">Voice Order</span>
            <span className="block text-[10px] text-brand font-medium">Gnani.ai</span>
          </div>
        </button>
      </aside>

      {/* Voice Order Modal */}
      {isOpen && <VoiceOrderModal onClose={() => setIsOpen(false)} />}
    </>
  );
}
