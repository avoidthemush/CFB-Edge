"use client";

import { useEffect, useState, useMemo } from "react";
import { Flame, Activity, Layers3, Building2 } from "lucide-react";
import FilterBar from "./components/FilterBar";
import GameRow from "./components/GameRow";

const API_BASE = "https://cfbedgeapi-production.up.railway.app";
const WEEKS = Array.from({ length: 15 }, (_, i) => i + 1);

function StatCard({ icon: Icon, label, value }) {
  return (
    <div className="bg-white/5 border border-white/10 rounded-xl px-5 py-4 flex items-center gap-3 flex-1 min-w-[140px]">
      <div className="bg-[#ee6c4d]/15 p-2 rounded-lg">
        <Icon size={18} className="text-[#ee6c4d]" />
      </div>
      <div>
        <p className="text-xl font-display font-bold text-white leading-none">{value}</p>
        <p className="text-xs text-[#98c1d9] mt-1">{label}</p>
      </div>
    </div>
  );
}

function dayKey(kickoff) {
  if (!kickoff) return "unknown";
  return new Date(kickoff).toLocaleDateString("en-US", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  });
}

function dayLabel(kickoff) {
  if (!kickoff) return "Date TBD";
  return new Date(kickoff).toLocaleDateString("en-US", {
    weekday: "long",
    month: "long",
    day: "numeric",
  });
}

function groupByDay(games) {
  const groups = [];
  let currentKey = null;
  let currentGroup = null;

  for (const game of games) {
    const key = dayKey(game.kickoff);
    if (key !== currentKey) {
      currentKey = key;
      currentGroup = { label: dayLabel(game.kickoff), games: [] };
      groups.push(currentGroup);
    }
    currentGroup.games.push(game);
  }

  return groups;
}

export default function Home() {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [week, setWeek] = useState(1);

  const [betType, setBetType] = useState("all");
  const [book, setBook] = useState("all");
  const [sortOrder, setSortOrder] = useState("soonest");
  const [onlyQualifying, setOnlyQualifying] = useState(false);

  useEffect(() => {
    setData(null);
    setError(null);
    fetch(`${API_BASE}/predictions/week/${week}`)
      .then((res) => {
        if (!res.ok) throw new Error(`API returned ${res.status}`);
        return res.json();
      })
      .then((json) => setData(json))
      .catch((err) => setError(err.message));
  }, [week]);

  const games = useMemo(() => {
    if (!data) return [];

    let filtered = data.games.map((g) => {
      let picks = g.picks;
      if (betType !== "all") picks = picks.filter((p) => p.bet_type === betType);
      if (book !== "all") picks = picks.filter((p) => p.book === book);
      return {
        matchup: g.matchup,
        kickoff: g.kickoff,
        venue: g.venue,
        weather: g.weather,
        awayTeam: g.away_team,
        homeTeam: g.home_team,
        picks,
      };
    });

    if (onlyQualifying) filtered = filtered.filter((g) => g.picks.length > 0);

    filtered.sort((a, b) => {
      const diff = new Date(a.kickoff) - new Date(b.kickoff);
      return sortOrder === "soonest" ? diff : -diff;
    });

    return filtered;
  }, [data, betType, book, sortOrder, onlyQualifying]);

  const dayGroups = useMemo(() => groupByDay(games), [games]);

  const distinctSystems = data
    ? new Set(data.games.flatMap((g) => g.picks.map((p) => p.system_name))).size
    : 0;
  const distinctBooks = data
    ? new Set(data.games.flatMap((g) => g.picks.map((p) => p.book)).filter(Boolean)).size
    : 0;

  return (
    <main className="min-h-screen bg-[#1b212b] p-6 md:p-8">
      <div className="max-w-6xl mx-auto">
        <div className="flex items-center gap-2 text-[#ee6c4d] text-xs font-bold uppercase tracking-wider mb-2">
          <Flame size={14} />
          <span>Live Edge Dashboard</span>
        </div>

        <div className="flex flex-wrap items-center justify-between gap-4 mb-6">
          <h1 className="text-3xl md:text-4xl font-display font-extrabold text-white">
            Week {week}
          </h1>

          <select
            value={week}
            onChange={(e) => setWeek(Number(e.target.value))}
            className="bg-white/5 border border-white/10 text-white text-sm font-semibold rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-[#ee6c4d]"
          >
            {WEEKS.map((w) => (
              <option key={w} value={w} className="text-black">
                Week {w}
              </option>
            ))}
          </select>
        </div>

        {error && <p className="text-[#ee6c4d] font-medium">Error loading games: {error}</p>}
        {!data && !error && <p className="text-[#98c1d9]">Loading...</p>}

        {data && (
          <>
            <div className="flex flex-wrap gap-3 mb-6">
              <StatCard icon={Activity} label="Games This Week" value={data.game_count} />
              <StatCard icon={Layers3} label="Games With Signal" value={data.games_with_signal} />
              <StatCard icon={Flame} label="Active Systems" value={distinctSystems} />
              <StatCard icon={Building2} label="Books Covered" value={distinctBooks} />
            </div>

            <FilterBar
              betType={betType}
              setBetType={setBetType}
              book={book}
              setBook={setBook}
              sortOrder={sortOrder}
              setSortOrder={setSortOrder}
            />

            <label className="flex items-center gap-2 text-sm text-[#98c1d9] mb-4 cursor-pointer w-fit">
              <input
                type="checkbox"
                checked={onlyQualifying}
                onChange={(e) => setOnlyQualifying(e.target.checked)}
                className="accent-[#ee6c4d]"
              />
              Only show games with a qualifying signal
            </label>

            {games.length === 0 ? (
              <div className="bg-white/5 border border-white/10 rounded-xl px-6 py-10 text-center">
                <p className="text-white/60 text-sm">No games found for Week {week}.</p>
              </div>
            ) : (
              <div className="flex flex-col gap-6">
                {dayGroups.map((group) => (
                  <div key={group.label} className="flex flex-col gap-3">
                    <div className="flex items-center gap-3">
                      <h2 className="text-sm font-bold text-white/70 uppercase tracking-wider whitespace-nowrap">
                        {group.label}
                      </h2>
                      <div className="h-px bg-white/10 flex-1" />
                    </div>
                    {group.games.map((game) => (
                      <GameRow key={`${game.matchup}__${game.kickoff}`} game={game} />
                    ))}
                  </div>
                ))}
              </div>
            )}
          </>
        )}
      </div>
    </main>
  );
}