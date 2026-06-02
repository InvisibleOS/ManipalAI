"use client";

import { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";

export default function DataLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const pathname = usePathname();

  const navItems = [
    {
      label: "Knowledge Base",
      href: "/data/knowledge-base",
      icon: (
        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
            d="M4 6h16M4 10h16M4 14h10M4 18h7" />
        </svg>
      ),
    },
    {
      label: "Announcements",
      href: "/data/announcements",
      icon: (
        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
            d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" />
        </svg>
      ),
    },
  ];

  return (
    <div className="flex flex-1 overflow-hidden">
      {/* Data Sidebar */}
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
              Data Management
            </p>
          </div>
        )}

        {/* Nav items */}
        <nav className="flex flex-col gap-1 p-3 pt-2">
          {navItems.map((item) => {
            const isActive = pathname === item.href;
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
