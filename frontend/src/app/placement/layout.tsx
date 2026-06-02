"use client";

import { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";

export default function PlacementLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const pathname = usePathname();

  const navItems = [
    {
      label: "Companies & Stats",
      href: "/placement",
      icon: (
        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
            d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
        </svg>
      ),
    },
    {
      label: "Question Bank",
      href: "/placement/question-bank",
      icon: (
        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
            d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
      ),
    },
    {
      label: "Company Calendar",
      href: "/placement/calendar",
      icon: (
        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
            d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
        </svg>
      ),
    },
  ];

  return (
    <div className="flex flex-1 overflow-hidden">
      {/* Placement Sidebar */}
      <aside
        className={`bg-white h-full border-r border-gray-100 flex flex-col transition-all duration-300 ease-in-out relative z-10 ${
          sidebarOpen ? "w-56" : "w-16"
        }`}
      >
        {/* Collapse toggle */}
        <button
          onClick={() => setSidebarOpen(!sidebarOpen)}
          className="absolute -right-3 top-1/2 -translate-y-1/2 bg-white border border-gray-200 rounded-full p-1 text-gray-400 hover:text-manipal-orange z-30 shadow-sm transition-colors"
        >
          <svg
            className={`w-3.5 h-3.5 transition-transform ${sidebarOpen ? "" : "rotate-180"}`}
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
          </svg>
        </button>

        {/* Section label */}
        {sidebarOpen && (
          <div className="px-4 pt-4 pb-2">
            <p className="text-[10px] font-semibold uppercase tracking-widest text-gray-400">
              Placement Hub
            </p>
          </div>
        )}

        {/* Nav items */}
        <nav className="flex flex-col gap-1 p-3 pt-2">
          {navItems.map((item) => {
            const isActive =
              item.href === "/placement"
                ? pathname === "/placement"
                : pathname.startsWith(item.href);
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`flex items-center gap-2.5 rounded-lg px-3 py-2 text-sm font-medium transition-all group ${
                  isActive
                    ? "bg-orange-50 text-manipal-orange border border-orange-100"
                    : "text-gray-600 hover:bg-gray-50 hover:text-gray-900"
                }`}
                title={!sidebarOpen ? item.label : undefined}
              >
                <span className={`shrink-0 ${isActive ? "text-manipal-orange" : "text-gray-400 group-hover:text-gray-600"}`}>
                  {item.icon}
                </span>
                {sidebarOpen && (
                  <span className="truncate">{item.label}</span>
                )}
              </Link>
            );
          })}
        </nav>
      </aside>

      {/* Page content */}
      <main className="flex-1 overflow-y-auto bg-slate-50">
        {children}
      </main>
    </div>
  );
}
