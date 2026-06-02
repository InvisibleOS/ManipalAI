"use client";

import { useCallback, useState } from "react";

interface IngestedDoc {
  id: string;
  title: string;
  type: string;
  chunks: number;
  ingestedAt: string;
}

export default function KnowledgeBasePage() {
  const [isDragging, setIsDragging] = useState(false);
  const [docs, setDocs] = useState<IngestedDoc[]>([]);
  const [uploading, setUploading] = useState(false);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback(() => {
    setIsDragging(false);
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    const files = Array.from(e.dataTransfer.files);
    handleFiles(files);
  }, []);

  const handleFileInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      handleFiles(Array.from(e.target.files));
    }
  };

  const handleFiles = (files: File[]) => {
    if (files.length === 0) return;
    setUploading(true);

    // Simulate ingestion
    setTimeout(() => {
      const newDocs: IngestedDoc[] = files.map((f) => ({
        id: Math.random().toString(36).slice(2),
        title: f.name,
        type: f.name.split(".").pop()?.toUpperCase() ?? "FILE",
        chunks: Math.floor(Math.random() * 40) + 5,
        ingestedAt: new Date().toLocaleString(),
      }));
      setDocs((prev) => [...prev, ...newDocs]);
      setUploading(false);
    }, 1200);
  };

  const deleteDoc = (id: string) => {
    setDocs((prev) => prev.filter((d) => d.id !== id));
  };

  return (
    <div className="p-8 max-w-4xl">
      {/* Page title */}
      <h1 className="text-2xl font-bold text-gray-900 mb-6">
        Knowledge Base Manager
      </h1>

      {/* Drop zone card */}
      <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-5 mb-5">
        <label
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          className={`flex flex-col items-center justify-center gap-3 border-2 border-dashed rounded-xl py-12 px-6 cursor-pointer transition-all ${
            isDragging
              ? "border-manipal-orange bg-orange-50"
              : "border-orange-300 hover:border-manipal-orange hover:bg-orange-50/40"
          }`}
        >
          <input
            type="file"
            multiple
            accept=".pdf,.xlsx,.txt,.docx"
            className="hidden"
            onChange={handleFileInput}
          />
          {uploading ? (
            <>
              <svg
                className="w-10 h-10 text-manipal-orange animate-spin"
                fill="none"
                viewBox="0 0 24 24"
              >
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z" />
              </svg>
              <p className="text-sm text-manipal-orange font-medium">Ingesting documents…</p>
            </>
          ) : (
            <>
              {/* Upload cloud icon */}
              <svg
                className="w-10 h-10 text-manipal-orange"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8}
                  d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
              </svg>
              <p className="text-sm text-gray-700 font-medium">
                Drag &amp; Drop files here or click to browse
              </p>
              <p className="text-xs text-gray-400">
                Supports .pdf, .xlsx, .txt, .docx
              </p>
            </>
          )}
        </label>
      </div>

      {/* Ingested documents table */}
      <div className="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden">
        <div className="flex items-center justify-between px-5 py-3.5 border-b border-gray-100">
          <p className="text-sm font-semibold text-gray-800">
            Ingested Documents ({docs.length})
          </p>
          <button
            onClick={() => setDocs([])}
            className="flex items-center gap-1.5 text-xs text-gray-500 hover:text-manipal-orange transition-colors"
          >
            <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
            Refresh
          </button>
        </div>

        {/* Table header */}
        <div className="grid grid-cols-[2fr_80px_80px_160px_100px] gap-4 px-5 py-2.5 bg-gray-50 border-b border-gray-100 text-xs font-semibold text-gray-500 uppercase tracking-wide">
          <span>Document Title</span>
          <span>Type</span>
          <span>Chunks</span>
          <span>Ingested At</span>
          <span className="text-right">Actions</span>
        </div>

        {docs.length === 0 ? (
          <div className="py-14 text-center text-sm text-gray-400">
            No documents ingested yet. Upload a file above to get started.
          </div>
        ) : (
          <ul className="divide-y divide-gray-50">
            {docs.map((doc) => (
              <li
                key={doc.id}
                className="grid grid-cols-[2fr_80px_80px_160px_100px] gap-4 px-5 py-3 items-center text-sm hover:bg-gray-50/60 transition-colors"
              >
                <span className="truncate font-medium text-gray-800">{doc.title}</span>
                <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-orange-50 text-manipal-orange border border-orange-100">
                  {doc.type}
                </span>
                <span className="text-gray-600">{doc.chunks}</span>
                <span className="text-gray-500 text-xs">{doc.ingestedAt}</span>
                <div className="flex justify-end">
                  <button
                    onClick={() => deleteDoc(doc.id)}
                    className="text-xs text-red-400 hover:text-red-600 transition-colors px-2 py-1 rounded hover:bg-red-50"
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
