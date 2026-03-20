"use client";

import { useEffect, useState } from "react";
import { SmartCard, fetchSmartCards } from "@/lib/api";

interface SmartCardsProps {
  folderName: string;
  onCardClick: (card: SmartCard) => void;
  visible: boolean;
}

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
      <div className="grid grid-cols-5 gap-2 mt-2">
        {cards.map((card) => (
          <button
            key={card.id}
            onClick={() => onCardClick(card)}
            className="group flex flex-col items-center justify-center text-center
                       bg-gradient-to-br from-gray-800 to-gray-900
                       border border-gray-700 rounded-xl p-3 h-36
                       hover:border-blue-500 hover:from-gray-700 hover:to-gray-800
                       transition-all duration-200 cursor-pointer"
          >
            <span className="text-2xl mb-1">{card.icon}</span>
            <span className="text-xs font-bold text-gray-200 leading-tight">
              {card.title}
            </span>
          </button>
        ))}
      </div>
    </div>
  );
}
