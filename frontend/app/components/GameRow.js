"use client";

import { Calendar, MapPin, Sun, CloudSun, CloudRain, CloudSnow, Wind, Snowflake } from "lucide-react";
import Image from "next/image";
import BetTypeBadge from "./BetTypeBadge";

const BOOK_LOGOS = {
  draftkings: { src: "/logos/draftkings.svg", label: "DraftKings" },
  fanduel: { src: "/logos/fanduel.svg", label: "FanDuel" },
};

function formatKickoff(kickoff) {
  if (!kickoff) return "-";
  const normalized = /[Zz]|[+-]\d{2}:\d{2}$/.test(kickoff) ? kickoff : `${kickoff}Z`;
  const date = new Date(normalized);

  const formatted = date.toLocaleString("en-US", {
    weekday: "short",
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });

  const zoneAbbrev = new Intl.DateTimeFormat("en-US", {
    timeZoneName: "short",
  })
    .formatToParts(date)
    .find((part) => part.type === "timeZoneName")?.value;

  return `${formatted}${zoneAbbrev ? ` ${zoneAbbrev}` : ""}`;
}

function splitMatchup(matchup) {
  const [away, home] = matchup.split(" @ ");
  return { away: away || matchup, home: home || "" };
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
  if (p.bet_type === "moneyline") {
    return p.system_historical_roi != null
      ? `${p.system_historical_roi > 0 ? "+" : ""}${p.system_historical_roi}% ROI`
      : "ROI unavailable";
  }
  return `${p.system_historical_win_rate}% win rate`;
}

function glowColor(distinctSystemCount) {
  if (distinctSystemCount >= 3) return "shadow-[inset_3px_0_0_0_#ee6c4d]";
  if (distinctSystemCount === 2) return "shadow-[inset_3px_0_0_0_#3d5a80]";
  return "shadow-[inset_3px_0_0_0_#98c1d9]";
}

function groupByBook(picks) {
  const groups = { draftkings: [], fanduel: [], other: [] };
  for (const p of picks) {
    if (p.book === "draftkings") groups.draftkings.push(p);
    else if (p.book === "fanduel") groups.fanduel.push(p);
    else groups.other.push(p);
  }
  return groups;
}

function WeatherIcon({ condition, size = 16 }) {
  const c = (condition || "").toLowerCase();
  if (c === "rain") return <CloudRain size={size} />;
  if (c === "snow") return <CloudSnow size={size} />;
  if (c === "windy") return <Wind size={size} />;
  if (c === "cold") return <Snowflake size={size} />;
  if (c === "clear") return <Sun size={size} />;
  return <CloudSun size={size} />;
}

function formatVenueLines(venue) {
  if (!venue) return null;
  const location = [venue.city, venue.state].filter((p) => p && p.trim().length > 0).join(", ");
  return { name: venue.name, location: location || null };
}

function TeamBlock({ team }) {
  return (
    <div>
      <p className="font-display font-bold text-white text-base leading-tight">
        {team?.name || "-"}
      </p>
      <div className="flex items-center gap-2 text-[11px] text-white/40 mt-0.5">
        <span>{team?.season_record ?? "0-0"}</span>
        {team?.recent_form && (
          <span className="text-white/30">L10 SU: {team.recent_form.su}</span>
        )}
      </div>
    </div>
  );
}

function BookColumn({ bookKey, picks }) {
  const meta = BOOK_LOGOS[bookKey];

  return (
    <div className="flex-1 min-w-[220px] bg-black/20 rounded-lg p-3 flex flex-col gap-2">
      <div className="flex items-center gap-2 pb-1 border-b border-white/10">
        {meta ? (
          <Image
            src={meta.src}
            alt={meta.label}
            width={80}
            height={20}
            style={{ width: "auto", height: "1.25rem" }}
          />
        ) : (
          <span className="text-xs font-bold text-white/60 uppercase">Other</span>
        )}
        <span className="text-[10px] text-white/30 ml-auto">
          {picks.length} signal{picks.length !== 1 ? "s" : ""}
        </span>
      </div>

      {picks.length === 0 ? (
        <p className="text-xs text-white/25 italic py-1">No qualifying signals</p>
      ) : (
        picks.map((p, i) => (
          <div key={i} className="flex flex-col gap-1 py-1">
            <div className="flex items-center gap-2 flex-wrap">
              <BetTypeBadge betType={p.bet_type} />
              <span className="text-sm font-medium text-white">{p.system_name}</span>
            </div>
            <span className="text-sm text-[#e0fbfc]">{betDescription(p)}</span>
            <div className="flex items-center justify-between">
              <span className="text-xs text-[#98c1d9]">
                Line: {p.market_line_current ?? "-"}
              </span>
              <span className="text-xs font-semibold text-[#ee6c4d]">
                {performanceLabel(p)}
              </span>
            </div>
          </div>
        ))
      )}
    </div>
  );
}

export default function GameRow({ game }) {
  const distinctSystems = Array.from(new Set(game.picks.map((p) => p.system_name)));
  const grouped = groupByBook(game.picks);
  const venue = formatVenueLines(game.venue);

  return (
    <div
      className={`bg-white/5 border border-white/10 rounded-xl overflow-hidden ${glowColor(
        distinctSystems.length
      )}`}
    >
      <div className="flex flex-col lg:flex-row gap-5 px-6 py-5">
        <div className="lg:w-64 shrink-0 flex flex-col gap-2">
          <TeamBlock team={game.awayTeam} />

          <div className="flex items-center gap-1.5 -my-0.5">
            <span className="text-xs font-bold text-[#ee6c4d]">@</span>
            <div className="h-px bg-white/10 flex-1" />
          </div>

          <TeamBlock team={game.homeTeam} />

          <div className="flex items-center gap-1.5 text-xs text-[#98c1d9] mt-1">
            <Calendar size={14} />
            <span>{formatKickoff(game.kickoff)}</span>
          </div>

          <div className="flex items-center gap-1.5 text-white/50">
            <MapPin size={14} className="shrink-0" />
            <div className="min-w-0 leading-tight">
              <p className="text-xs truncate">{venue?.name || "TBD"}</p>
              {venue?.location && (
                <p className="text-[11px] text-white/35 truncate">{venue.location}</p>
              )}
            </div>
          </div>

          <div className="flex items-center gap-1 text-white/50">
            <WeatherIcon condition={game.weather?.condition} size={14} />
            <span className="text-xs">
              {game.weather?.temp_f != null ? `${Math.round(game.weather.temp_f)}°F` : "TBD"}
            </span>
          </div>
        </div>

        <div className="flex-1 flex flex-col sm:flex-row gap-3 min-w-0">
          <BookColumn bookKey="draftkings" picks={grouped.draftkings} />
          <BookColumn bookKey="fanduel" picks={grouped.fanduel} />
          {grouped.other.length > 0 && (
            <BookColumn bookKey="other" picks={grouped.other} />
          )}
        </div>
      </div>
    </div>
  );
}