"use client";

import { useState } from "react";
import {
  questions,
  companies,
  tagColors,
  type CompanyName,
} from "../data";

export default function QuestionBankPage() {
  const [companyFilter, setCompanyFilter] = useState<"All" | CompanyName>("All");
  const [search, setSearch] = useState("");

  const filteredQuestions = questions.filter((q) => {
    const matchCompany = companyFilter === "All" || q.company === companyFilter;
    const matchSearch =
      q.q.toLowerCase().includes(search.toLowerCase()) ||
      q.company.toLowerCase().includes(search.toLowerCase()) ||
      q.tags.some((t) => t.toLowerCase().includes(search.toLowerCase()));
    return matchCompany && matchSearch;
  });

  return (
    <div className="p-8 max-w-5xl">
      {/* Header */}
      <div className="mb-6">
        <h1
          className="text-2xl font-semibold text-gray-900"
          style={{ letterSpacing: "-0.02em" }}
        >
          Question Bank
        </h1>
        <p className="text-xs text-gray-400 mt-0.5">
          Real interview questions from past placement drives
        </p>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap items-center gap-3 mb-6">
        <select
          value={companyFilter}
          onChange={(e) => setCompanyFilter(e.target.value as "All" | CompanyName)}
          className="border border-gray-200 rounded-xl px-3 py-2 text-xs text-gray-700 bg-white focus:outline-none focus:ring-2 focus:ring-orange-200 focus:border-manipal-orange transition-all"
        >
          <option value="All">All Companies</option>
          {companies.map((c) => (
            <option key={c.name} value={c.name}>
              {c.name}
            </option>
          ))}
        </select>

        <input
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search questions or tags…"
          className="flex-1 min-w-[200px] border border-gray-200 rounded-xl px-4 py-2 text-xs text-gray-700 placeholder-gray-300 bg-white focus:outline-none focus:ring-2 focus:ring-orange-200 focus:border-manipal-orange transition-all"
        />
      </div>

      {/* Questions list */}
      <div className="space-y-3">
        {filteredQuestions.length === 0 ? (
          <div className="text-center py-14 text-sm text-gray-400">
            No questions match your filters.
          </div>
        ) : (
          filteredQuestions.map((q, i) => (
            <div
              key={i}
              className="bg-white border border-gray-100 rounded-2xl p-5 shadow-sm hover:shadow-md transition-shadow"
            >
              <div className="flex items-center gap-2 mb-2">
                <span className="text-xs font-semibold text-gray-800">
                  {q.company}
                </span>
                <span className="text-gray-300">·</span>
                <span className="text-xs text-gray-500">{q.role}</span>
                <span className="text-gray-300">·</span>
                <span className="text-xs text-gray-400">{q.round}</span>
              </div>

              <p className="text-sm text-gray-700 mb-3 leading-relaxed">
                {q.q}
              </p>

              <div className="flex flex-wrap gap-1.5">
                {q.tags.map((tag) => (
                  <span
                    key={tag}
                    className={`px-2 py-0.5 rounded-full text-[10px] font-medium ${tagColors[tag]}`}
                  >
                    {tag}
                  </span>
                ))}
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
