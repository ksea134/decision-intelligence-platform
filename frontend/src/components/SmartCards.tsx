"use client";

import { useEffect, useState } from "react";
import { SmartCard, fetchSmartCards, API_BASE } from "@/lib/api";

interface SmartCardsProps {
  folderName: string;
  onCardClick: (card: SmartCard) => void;
  visible: boolean;
}

const DOMAIN_COLORS: Record<string, string> = {
  "工場": "bg-green-900/50 text-green-400",
  "品質": "bg-blue-900/50 text-blue-400",
  "安全": "bg-amber-900/50 text-amber-400",
  "監査": "bg-purple-900/50 text-purple-400",
  "経営": "bg-cyan-900/50 text-cyan-400",
  "在庫": "bg-orange-900/50 text-orange-400",
};

export default function SmartCards({ folderName, onCardClick, visible }: SmartCardsProps) {
  const [cards, setCards] = useState<SmartCard[]>([]);

  useEffect(() => {
    if (folderName) {
      fetchSmartCards(folderName).then(setCards);
    }
  }, [folderName]);

  if (!visible || cards.length === 0) return null;

  return (
    <div className="mb-6">
      <span className="text-xs text-gray-400 tracking-wider">DI Dashboard</span>
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-2 mt-2">
        {cards.map((card) => (
          <button
            key={card.id}
            onClick={() => onCardClick(card)}
            className="group flex flex-col items-center justify-center text-center
                       bg-gradient-to-br from-gray-800 to-gray-900
                       border border-gray-700 rounded-xl p-3 h-28 md:h-36
                       hover:border-[#29707A] hover:from-gray-700 hover:to-gray-800
                       transition-all duration-200 cursor-pointer relative"
          >
            {card.domain && (
              <span className={`absolute top-1.5 right-1.5 text-[9px] px-1.5 py-0.5 rounded-full ${DOMAIN_COLORS[card.domain] || "bg-gray-700 text-gray-400"}`}>
                {card.domain}
              </span>
            )}
            {card.icon_type === "image" ? (
              <img src={`${card.icon.startsWith("http") ? "" : API_BASE}${card.icon}`} alt="" className="w-8 h-8 mb-1 object-contain" />
            ) : card.icon_type === "symbol" ? (
              <span className="material-symbols-outlined text-2xl mb-1">{card.icon}</span>
            ) : (
              <span className="text-2xl mb-1">{card.icon}</span>
            )}
            <span className="text-xs font-bold text-gray-200 leading-tight">
              {card.title}
            </span>
            {card.period && (
              <span className="text-[11px] text-gray-500 mt-0.5">
                {card.period}
              </span>
            )}
            {card.timing && (
              <span className="absolute top-1.5 left-1.5 text-[11px] text-gray-500">
                {card.timing}
              </span>
            )}
          </button>
        ))}
      </div>
    </div>
  );
}
