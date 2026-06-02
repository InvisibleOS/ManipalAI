import type { Metadata } from "next";
import { Poppins } from "next/font/google";
import "./globals.css";
import Link from "next/link";

const poppins = Poppins({
  weight: ['300', '400', '500', '600'],
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Campus Assistant | Manipal",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className={`${poppins.className} flex flex-col h-screen bg-white m-0 p-0 overflow-hidden`}>

        {/* Top Header */}
        <header
          className="flex items-center justify-between px-6 shrink-0 z-20 relative text-white shadow-md"
          style={{
            height: '60px',
            backgroundColor: '#f37021'
          }}
        >
          <div className="flex items-center gap-3">
            <Link
              href="/"
              className="w-8 h-8 rounded-lg bg-white/10 hover:bg-white/20 border border-white/20 hover:border-white/40 flex items-center justify-center transition-all"
              title="Home"
            >
              <svg className="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-4 0a1 1 0 01-1-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 01-1 1h-2z" />
              </svg>
            </Link>
            <div className="flex flex-col justify-center">
              <h1 className="text-base font-semibold leading-tight tracking-wide text-white">
                MIT Bengaluru Virtual Assistant
              </h1>
              <p className="text-[11px] text-white/80 font-light mt-0.5">
                Empowered by AI &middot; Ask me anything
              </p>
            </div>
          </div>
          <div className="flex items-center gap-4">
            <Link
              href="/placement"
              className="text-xs text-white border border-white/30 hover:border-white/50 hover:bg-white/10 rounded px-3 py-1.5 font-medium transition-all"
            >
              Placement Hub
            </Link>
            <Link
              href="/data"
              className="text-xs text-white border border-white/30 hover:border-white/50 hover:bg-white/10 rounded px-3 py-1.5 font-medium transition-all"
            >
              Manage Data
            </Link>
            <button className="w-8 h-8 rounded-full border border-white/30 bg-white/10 hover:bg-white/20 hover:border-white/50 flex items-center justify-center text-sm font-semibold text-white transition-all cursor-pointer" title="Profile">
              S
            </button>
          </div>
        </header>


        <div className="flex-1 flex overflow-hidden relative">
          {children}
        </div>
      </body>
    </html>
  );
}