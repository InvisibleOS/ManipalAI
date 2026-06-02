"use client";

import { useState } from "react";
import { stats, companies, sectors, logoColors, type Sector } from "./data";

export default function CompaniesAndStats() {
  const [sectorFilter, setSectorFilter] = useState<"All" | Sector>("All");

  const filteredCompanies = companies.filter(
    (c) => sectorFilter === "All" || c.sector === sectorFilter
  );

  return (
    <div className="p-8 max-w-5xl">
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
            Live data · Class of 2024–25 · Manipal Institute of Technology
          </p>
        </div>
        <span className="text-xs bg-green-50 border border-green-200 text-green-600 font-medium px-3 py-1 rounded-full">
          Season Active
        </span>
      </div>

      {/* Stat cards */}
      <div className="grid grid-cols-4 gap-4 mb-8">
        {stats.map((s) => (
          <div
            key={s.label}
            className="bg-white border border-gray-100 rounded-2xl p-4 shadow-sm"
          >
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
            className={`px-3.5 py-1.5 rounded-full text-xs font-medium transition-all ${
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