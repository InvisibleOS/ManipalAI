"use client";

import { calendar, calColors, logoColors } from "../data";

export default function CompanyCalendarPage() {
  return (
    <div className="p-8 max-w-4xl">
      {/* Header */}
      <div className="mb-6">
        <h1
          className="text-2xl font-semibold text-gray-900"
          style={{ letterSpacing: "-0.02em" }}
        >
          Company Calendar
        </h1>
        <p className="text-xs text-gray-400 mt-0.5">
          Upcoming placement events and deadlines
        </p>
      </div>

      {/* Timeline */}
      <div className="space-y-3">
        {calendar.map((ev, i) => (
          <div
            key={i}
            className={`flex items-center gap-5 bg-white border rounded-2xl px-5 py-4 shadow-sm hover:shadow-md transition-shadow ${calColors[ev.color]}`}
          >
            {/* Date block */}
            <div className="text-center shrink-0 w-14">
              <p className="text-lg font-bold leading-tight">{ev.date.split(" ")[0]}</p>
              <p className="text-[10px] font-medium uppercase tracking-wide opacity-70">
                {ev.date.split(" ")[1]}
              </p>
              <p className="text-[10px] opacity-50">{ev.day}</p>
            </div>

            {/* Divider */}
            <div className="w-px h-10 bg-current opacity-15 shrink-0" />

            {/* Info */}
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 mb-0.5">
                <div
                  className={`w-6 h-6 rounded-lg flex items-center justify-center text-[9px] font-bold ${logoColors[ev.company]}`}
                >
                  {ev.company.slice(0, 2)}
                </div>
                <p className="text-sm font-semibold truncate">{ev.company}</p>
              </div>
              <p className="text-xs opacity-70">{ev.role}</p>
            </div>

            {/* Event type badge */}
            <span className="shrink-0 text-[11px] font-medium px-3 py-1 rounded-full bg-white/50 border border-current/10">
              {ev.type}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
