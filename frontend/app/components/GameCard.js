"use client";

import { useState } from "react";
import { ChevronDown, ChevronUp } from "lucide-react";
import BetTypeBadge from "./BetTypeBadge";
import BookBadge from "./BookBadge";

function formatKickoff(kickoff) {
  if (!kickoff) return "-";
  return new Date(kickoff).toLocaleString(undefined, {
    weekday: "short",
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

function betDescription(p) {
  if (p.bet_type === "moneyline") {
    const sign = p.predicted_value > 0 ? "+" : "";
    return `${p.bet_on_home ? "HOME" : "AWAY"} dog ML ${sign}${p.predicted_value}`;
  }
  if (p.bet_type === "spread") {
    return `${p.bet_on_home ? "HOME" : "AWAY"} @ ${(p.confidence * 100).toFixed(1)}%`;
  }
  const dir = p.predicted_value > 0 ? "UNDER" : "OVER";
  return `${dir} (dev ${p.predicted_value.toFixed(1)})`;
}

function performanceLabel(p) {
  if (p.bet_type === "moneyline") return "See ROI (not win %)";
  return `${p.system_historical_win_rate}% win rate`;
}

export default function GameCard({ game }) {
  const [expanded, setExpanded] = useState(false);

  const distinctBetTypes = Array.from(
    new Set(game.picks.map((p) => p.bet_type))
  );

  return (
    <div className="bg-white rounded-lg shadow overflow-hidden">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full text-left px-5 py-4 flex items-center justify-between gap-4"
      >
        <div className="min-w-0">
          <p className="font-semibold text-[#293241] truncate">{game.matchup}</p>
          <p className="text-xs text-[#3d5a80] mt-1">{formatKickoff(game.kickoff)}</p>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          {distinctBetTypes.map((bt) => (
            <BetTypeBadge key={bt} betType={bt} />
          ))}
          {expanded ? (
            <ChevronUp size={18} className="text-[#3d5a80]" />
          ) : (
            <ChevronDown size={18} className="text-[#3d5a80]" />
          )}
        </div>
      </button>

      {expanded && (
        <div className="border-t border-[#98c1d9]/30 divide-y divide-[#98c1d9]/20">
          {game.picks.map((p, i) => (
            <div key={i} className="px-5 py-3 flex flex-col gap-1">
              <div className="flex items-center gap-2 flex-wrap">
                <BetTypeBadge betType={p.bet_type} />
                {p.book && <BookBadge book={p.book} />}
                <span className="text-sm font-medium text-[#293241]">
                  {p.system_name}
                </span>
              </div>
              <div className="text-sm text-[#293241]">{betDescription(p)}</div>
              <div className="text-xs text-[#3d5a80]">
                Market line: {p.market_spread_current ?? "-"}
              </div>
              <div className="text-xs font-medium text-[#ee6c4d]">
                {performanceLabel(p)}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}