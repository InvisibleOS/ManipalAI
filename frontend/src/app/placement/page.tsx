"use client";

import { useState, useEffect } from "react";
import { stats as defaultStats, companies as defaultCompanies, sectors, logoColors, type Sector } from "./data";

interface StatItem {
  label: string;
  value: string;
  sub: string;
}

export default function CompaniesAndStats() {
  const [stats, setStats] = useState<StatItem[]>(defaultStats);
  const [companies, setCompanies] = useState(defaultCompanies);
  const [sectorFilter, setSectorFilter] = useState<"All" | Sector>("All");
  const [isLive, setIsLive] = useState(false);
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    async function fetchStats() {
      try {
        setIsLoading(true);
        const baseUrl = process.env.NEXT_PUBLIC_API_URL || "https://manipal-chatbot.onrender.com";
        const res = await fetch(`${baseUrl}/mock/placement-stats`);
        if (!res.ok) {
          throw new Error(`HTTP error! status: ${res.status}`);
        }
        
        const resJson = await res.json();
        const rootData = resJson.data || resJson;
        
        // Match the database array format
        const recordList = Array.isArray(rootData) ? rootData : null;
        
        if (recordList && recordList.length > 0) {
          const record = recordList[0];
          const mappedStats = [
            { 
              label: "Students Placed", 
              value: String(record.placed_students || 847), 
              sub: `Out of ${record.total_students || 1000} (Class of 2024)` 
            },
            { 
              label: "Avg. Package", 
              value: `₹${record.average_salary_lpa || 12.4}L`, 
              sub: "Per annum" 
            },
            { 
              label: "Highest Package", 
              value: `₹${record.highest_salary_lpa || 48}L`, 
              sub: `${record.top_company || "Google"} — 2024` 
            },
            { 
              label: "Companies Visited", 
              value: "134", 
              sub: "This year" 
            }
          ];
          setStats(mappedStats);
          setIsLive(true);
        } else if (rootData.stats && Array.isArray(rootData.stats)) {
          // Alternative nested format
          setStats(rootData.stats);
          setIsLive(true);
        }
      } catch (error) {
        console.warn("Failed to fetch live placement stats, using mock fallback data:", error);
      } finally {
        setIsLoading(false);
      }
    }

    fetchStats();
  }, []);

  const filteredCompanies = companies.filter(
    (c) => sectorFilter === "All" || c.sector === sectorFilter
  );

  return (
    <div className="p-8 max-w-5xl w-full mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1
            className="text-2xl font-semibold text-gray-900"
            style={{ letterSpacing: "-0.02em" }}
          >
            Companies &amp; Stats
          </h1>
          <p className="text-xs text-gray-400 mt-0.5">
            {isLive ? "Live API Data" : "Mock Data"} · Class of 2024–25 · Manipal Institute of Technology
          </p>
        </div>
        <div className="flex items-center gap-2">
          {isLive ? (
            <span className="text-[10px] bg-emerald-50 border border-emerald-200 text-emerald-600 font-semibold px-2.5 py-1 rounded-full flex items-center gap-1.5 animate-pulse">
              <span className="w-1.5 h-1.5 bg-emerald-500 rounded-full" />
              Live API
            </span>
          ) : (
            <span className="text-[10px] bg-slate-50 border border-slate-200 text-slate-500 font-semibold px-2.5 py-1 rounded-full flex items-center gap-1.5">
              <span className="w-1.5 h-1.5 bg-slate-400 rounded-full" />
              Offline
            </span>
          )}
          <span className="text-[10px] bg-green-50 border border-green-200 text-green-600 font-semibold px-2.5 py-1 rounded-full">
            Season Active
          </span>
        </div>
      </div>

      {/* Stat cards */}
      <div className="grid grid-cols-4 gap-4 mb-8">
        {stats.map((s) => (
          <div
            key={s.label}
            className="bg-white border border-gray-100 rounded-2xl p-4 shadow-sm hover:shadow-md transition-shadow relative overflow-hidden"
          >
            {isLoading && (
              <div className="absolute inset-0 bg-white/50 flex items-center justify-center">
                <span className="w-4 h-4 border-2 border-manipal-orange border-t-transparent rounded-full animate-spin" />
              </div>
            )}
            <p className="text-xs text-gray-400 mb-1">{s.label}</p>
            <p
              className="text-2xl font-semibold text-gray-900"
              style={{ letterSpacing: "-0.02em" }}
            >
              {s.value}
            </p>
            <p className="text-[10px] text-gray-400 mt-0.5">{s.sub}</p>
          </div>
        ))}
      </div>

      {/* Sector filter */}
      <div className="flex gap-2 mb-5">
        {sectors.map((s) => (
          <button
            key={s}
            onClick={() => setSectorFilter(s)}
            className={`px-3.5 py-1.5 rounded-full text-xs font-medium transition-all cursor-pointer ${
              sectorFilter === s
                ? "bg-manipal-orange text-white shadow-sm"
                : "bg-white border border-gray-200 text-gray-500 hover:border-orange-200 hover:text-manipal-orange"
            }`}
          >
            {s}
          </button>
        ))}
      </div>

      {/* Company cards */}
      <div className="grid grid-cols-2 gap-4">
        {filteredCompanies.map((c) => (
          <div
            key={c.name}
            className="bg-white border border-gray-100 rounded-2xl p-5 shadow-sm hover:shadow-md transition-shadow"
          >
            <div className="flex items-center gap-3 mb-3">
              <div
                className={`w-9 h-9 rounded-xl flex items-center justify-center text-xs font-bold ${logoColors[c.name]}`}
              >
                {c.logo}
              </div>
              <div>
                <p className="text-sm font-semibold text-gray-800">{c.name}</p>
                <p className="text-[11px] text-gray-400">{c.sector}</p>
              </div>
            </div>
            <div className="grid grid-cols-3 gap-3 text-center">
              <div>
                <p className="text-lg font-semibold text-gray-900">{c.placed}</p>
                <p className="text-[10px] text-gray-400">Placed</p>
              </div>
              <div>
                <p className="text-lg font-semibold text-gray-900">{c.avg}</p>
                <p className="text-[10px] text-gray-400">Avg. CTC</p>
              </div>
              <div>
                <p className="text-lg font-semibold text-gray-900">{c.high}</p>
                <p className="text-[10px] text-gray-400">Highest</p>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}