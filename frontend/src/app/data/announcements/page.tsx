"use client";

import { useState } from "react";

interface Announcement {
  id: string;
  title: string;
  content: string;
  publishedAt: string;
}

export default function AnnouncementsPage() {
  const [title, setTitle] = useState("");
  const [content, setContent] = useState("");
  const [publishing, setPublishing] = useState(false);
  const [announcements, setAnnouncements] = useState<Announcement[]>([]);
  const [error, setError] = useState("");

  const handlePublish = () => {
    if (!title.trim() || !content.trim()) {
      setError("Both fields are required.");
      return;
    }
    setError("");
    setPublishing(true);

    // Simulate vectorization + publish
    setTimeout(() => {
      setAnnouncements((prev) => [
        {
          id: Math.random().toString(36).slice(2),
          title: title.trim(),
          content: content.trim(),
          publishedAt: new Date().toLocaleString(),
        },
        ...prev,
      ]);
      setTitle("");
      setContent("");
      setPublishing(false);
    }, 1200);
  };

  const deleteAnnouncement = (id: string) => {
    setAnnouncements((prev) => prev.filter((a) => a.id !== id));
  };

  return (
    <div className="p-8 max-w-3xl">
      {/* Page title */}
      <h1 className="text-2xl font-bold text-gray-900 mb-6">
        Announcements Center
      </h1>

      {/* Push form card */}
      <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6 mb-5">
        <h2 className="text-base font-semibold text-gray-900 mb-4">
          Push High-Priority Context
        </h2>

        {error && (
          <p className="mb-3 text-xs text-red-500 bg-red-50 border border-red-100 rounded-lg px-3 py-2">
            {error}
          </p>
        )}

        <div className="mb-4">
          <label className="block text-xs text-gray-500 font-medium mb-1.5">
            Announcement Title
          </label>
          <input
            type="text"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="e.g. End Semester Exam Scheduling Update"
            className="w-full border border-gray-200 rounded-xl px-4 py-2.5 text-sm text-gray-800 placeholder-gray-300 focus:outline-none focus:ring-2 focus:ring-orange-200 focus:border-manipal-orange transition-all"
          />
        </div>

        <div className="mb-5">
          <label className="block text-xs text-gray-500 font-medium mb-1.5">
            Detailed Content
          </label>
          <textarea
            value={content}
            onChange={(e) => setContent(e.target.value)}
            rows={5}
            placeholder="Enter the full context. This will be embedded into the vector DB for top-priority RAG retrieval."
            className="w-full border border-gray-200 rounded-xl px-4 py-2.5 text-sm text-gray-800 placeholder-gray-300 focus:outline-none focus:ring-2 focus:ring-orange-200 focus:border-manipal-orange transition-all resize-none"
          />
        </div>

        <button
          onClick={handlePublish}
          disabled={publishing}
          className="w-full bg-manipal-orange hover:bg-orange-600 disabled:opacity-60 disabled:cursor-not-allowed text-white font-semibold py-3 rounded-xl transition-all flex items-center justify-center gap-2 shadow-md hover:shadow-lg"
        >
          {publishing ? (
            <>
              <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z" />
              </svg>
              Vectorizing…
            </>
          ) : (
            "Vectorize & Publish Announcement"
          )}
        </button>
      </div>

      {/* Published list */}
      <div className="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden">
        <div className="flex items-center justify-between px-5 py-3.5 border-b border-gray-100">
          <p className="text-sm font-semibold text-gray-800">
            Published Announcements ({announcements.length})
          </p>
          <button
            onClick={() => setAnnouncements([])}
            className="flex items-center gap-1.5 text-xs text-gray-500 hover:text-manipal-orange transition-colors"
          >
            <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
            Refresh
          </button>
        </div>

        {announcements.length === 0 ? (
          <div className="py-14 text-center text-sm text-gray-400">
            No announcements yet. Post one above.
          </div>
        ) : (
          <ul className="divide-y divide-gray-50">
            {announcements.map((a) => (
              <li key={a.id} className="px-5 py-4 hover:bg-gray-50/60 transition-colors">
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-semibold text-gray-800 truncate">{a.title}</p>
                    <p className="text-xs text-gray-500 mt-0.5 line-clamp-2">{a.content}</p>
                    <p className="text-[11px] text-gray-400 mt-1">{a.publishedAt}</p>
                  </div>
                  <button
                    onClick={() => deleteAnnouncement(a.id)}
                    className="shrink-0 text-xs text-red-400 hover:text-red-600 transition-colors px-2 py-1 rounded hover:bg-red-50"
                  >
                    Delete
                  </button>
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
