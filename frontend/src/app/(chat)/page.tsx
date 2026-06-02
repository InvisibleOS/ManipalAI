import ChatInput from '@/components/ChatInput';

export default function Home() {
  return (
    <main className="flex-1 relative flex flex-col h-full bg-slate-100/30 overflow-hidden">

      {/* Main centred content */}
      <div className="flex-1 overflow-y-auto flex flex-col items-center justify-center px-8 z-10 relative">
        <h1
          className="text-5xl font-light text-gray-900 mb-3 text-center"
          style={{ letterSpacing: '-0.03em' }}
        >
          Welcome
        </h1>
        <p className="text-sm text-gray-400 font-normal mb-10 text-center">
          Your Manipal Campus AI Assistant
        </p>

        <div className="flex flex-wrap justify-center gap-2.5 max-w-xl">
          {[
            'Help with Resume ATS',
            'Practice Behavioral Interview',
            'Company question bank',
            'Upcoming placements',
            'Check my schedule',
          ].map((label) => (
            <button
              key={label}
              className="px-4 py-2 bg-white border border-gray-200 rounded-full text-xs text-gray-600 shadow-sm hover:shadow-md hover:border-orange-200 hover:text-manipal-orange transition-all"
            >
              {label}
            </button>
          ))}
        </div>
      </div>

      {/* Input bar */}
      <div className="p-5 pb-10 w-full z-10 relative flex justify-center">
        <ChatInput />
      </div>
    </main>
  );
}