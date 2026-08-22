"use client";

import { useEffect, useState, useMemo } from "react";
import { Flame, Activity, Layers3, Building2 } from "lucide-react";
import FilterBar from "./components/FilterBar";
import GameRow from "./components/GameRow";

const API_BASE = "https://cfbedgeapi-production.up.railway.app";

function groupByGame(predictions) {
  const map = new Map();
  for (const p of predictions) {
    const key = `${p.matchup}__${p.kickoff}`;
    if (!map.has(key)) {
      map.set(key, {
        matchup: p.matchup,
        kickoff: p.kickoff,
        venue: p.venue,
        weather: p.weather,
        awayTeam: p.away_team,
        homeTeam: p.home_team,
        picks: [],
      });
    }
    map.get(key).picks.push(p);
  }
  return Array.from(map.values());
}

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

export default function Home() {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [week, setWeek] = useState(1);

  const [betType, setBetType] = useState("all");
  const [book, setBook] = useState("all");
  const [sortOrder, setSortOrder] = useState("soonest");

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
    let picks = data.predictions;
    if (betType !== "all") picks = picks.filter((p) => p.bet_type === betType);
    if (book !== "all") picks = picks.filter((p) => p.book === book);
    const grouped = groupByGame(picks);
    grouped.sort((a, b) => {
      const diff = new Date(a.kickoff) - new Date(b.kickoff);
      return sortOrder === "soonest" ? diff : -diff;
    });
    return grouped;
  }, [data, betType, book, sortOrder]);

  const distinctSystems = data ? new Set(data.predictions.map((p) => p.system_name)).size : 0;
  const distinctBooks = data ? new Set(data.predictions.map((p) => p.book).filter(Boolean)).size : 0;

  return (
    <main className="min-h-screen bg-[#1b212b] p-6 md:p-8">
      <div className="max-w-6xl mx-auto">
        <div className="flex items-center gap-2 text-[#ee6c4d] text-xs font-bold uppercase tracking-wider mb-2">
          <Flame size={14} />
          <span>Live Edge Dashboard</span>
        </div>
        <h1 className="text-3xl md:text-4xl font-display font-extrabold text-white mb-6">
          Week {week} Picks
        </h1>

        <div className="mb-6 flex gap-2 flex-wrap">
          {[1, 2, 3].map((w) => (
            <button
              key={w}
              onClick={() => setWeek(w)}
              className={`px-4 py-2 rounded-lg font-semibold text-sm transition-colors ${
                week === w
                  ? "bg-[#ee6c4d] text-white"
                  : "bg-white/5 text-white/70 border border-white/10 hover:bg-white/10"
              }`}
            >
              Week {w}
            </button>
          ))}
        </div>

        {error && <p className="text-[#ee6c4d] font-medium">Error loading picks: {error}</p>}
        {!data && !error && <p className="text-[#98c1d9]">Loading...</p>}

        {data && (
          <>
            <div className="flex flex-wrap gap-3 mb-6">
              <StatCard icon={Activity} label="Qualifying Games" value={games.length} />
              <StatCard icon={Layers3} label="Total Signals" value={data.count} />
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

            <div className="flex flex-col gap-3">
              {games.map((game) => (
                <GameRow key={`${game.matchup}__${game.kickoff}`} game={game} />
              ))}
            </div>
          </>
        )}
      </div>
    </main>
  );
}