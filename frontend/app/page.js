"use client";

import { useEffect, useState } from "react";

const API_BASE = "https://cfbedgeapi-production.up.railway.app";

export default function Home() {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [week, setWeek] = useState(1);

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

  return (
    <main className="min-h-screen bg-[#e0fbfc] p-8">
      <h1 className="text-3xl font-bold text-[#293241] mb-2">CFB Edge</h1>
      <p className="text-[#3d5a80] mb-6">Week {week} qualifying picks</p>

      <div className="mb-6 flex gap-2">
        {[1, 2, 3].map((w) => (
          <button
            key={w}
            onClick={() => setWeek(w)}
            className={`px-4 py-2 rounded-md font-medium border ${
              week === w
                ? "bg-[#3d5a80] text-white border-[#3d5a80]"
                : "bg-white text-[#293241] border-[#98c1d9]"
            }`}
          >
            Week {w}
          </button>
        ))}
      </div>

      {error && (
        <p className="text-[#ee6c4d] font-medium">Error loading picks: {error}</p>
      )}

      {!data && !error && (
        <p className="text-[#3d5a80]">Loading...</p>
      )}

      {data && (
        <>
          <p className="text-sm text-[#3d5a80] mb-4">
            {data.count} qualifying picks
          </p>
          <div className="overflow-x-auto bg-white rounded-lg shadow">
            <table className="min-w-full text-sm text-left">
              <thead className="bg-[#3d5a80] text-white uppercase text-xs">
                <tr>
                  <th className="px-4 py-3">Matchup</th>
                  <th className="px-4 py-3">Kickoff</th>
                  <th className="px-4 py-3">System</th>
                  <th className="px-4 py-3">Book</th>
                  <th className="px-4 py-3">Bet</th>
                  <th className="px-4 py-3">Market Line</th>
                  <th className="px-4 py-3">Edge</th>
                  <th className="px-4 py-3">Historical Performance</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#98c1d9]/30">
                {data.predictions.map((p, i) => (
                  <tr key={i} className="hover:bg-[#98c1d9]/10">
                    <td className="px-4 py-3 font-medium text-[#293241]">
                      {p.matchup}
                    </td>
                    <td className="px-4 py-3 text-[#3d5a80]">
                      {p.kickoff
                        ? new Date(p.kickoff).toLocaleString(undefined, {
                            month: "short",
                            day: "numeric",
                            hour: "numeric",
                            minute: "2-digit",
                          })
                        : "-"}
                    </td>
                    <td className="px-4 py-3 text-[#293241]">{p.system_name}</td>
                    <td className="px-4 py-3 capitalize text-[#293241]">
                      {p.book || "-"}
                    </td>
                    <td className="px-4 py-3 text-[#293241]">
                      {p.bet_type === "moneyline"
                        ? `${p.bet_on_home ? "HOME" : "AWAY"} dog ML ${p.predicted_value > 0 ? "+" : ""}${p.predicted_value}`
                        : p.bet_type === "spread"
                        ? `${p.bet_on_home ? "HOME" : "AWAY"} @ ${(p.confidence * 100).toFixed(1)}%`
                        : `${p.predicted_value > 0 ? "UNDER" : "OVER"} (dev ${p.predicted_value.toFixed(1)})`}
                    </td>
                    <td className="px-4 py-3 text-[#3d5a80]">
                      {p.market_spread_current ?? "-"}
                    </td>
                    <td className="px-4 py-3 text-[#3d5a80]">
                      {p.bet_type === "spread"
                        ? `${(p.confidence * 100).toFixed(1)}% confidence`
                        : p.bet_type === "total"
                        ? `${p.predicted_value > 0 ? "+" : ""}${p.predicted_value.toFixed(1)} deviation`
                        : "-"}
                    </td>
                    <td className="px-4 py-3 font-medium text-[#ee6c4d]">
                      {p.bet_type === "moneyline"
                        ? "See ROI (not win %)"
                        : `${p.system_historical_win_rate}% win rate`}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </main>
  );
}