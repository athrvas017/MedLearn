import React from 'react';

interface TopAppBarProps {
  isBackendHealthy: boolean;
  onClearChat: () => void;
  activeMobileTab: string;
  setActiveMobileTab: (tab: string) => void;
}

export const TopAppBar: React.FC<TopAppBarProps> = ({
  isBackendHealthy,
  onClearChat,
}) => {
  return (
    <header className="fixed top-0 w-full z-50 border-b border-outline/30 bg-inverse-surface/80 glass flex justify-between items-center px-4 md:px-6 mx-auto h-16 transition-all">
      {/* Brand Logo */}
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 rounded-xl bg-primary/20 border border-primary/30 flex items-center justify-center glow-teal">
          <span
            className="material-symbols-outlined text-primary-fixed text-[26px]"
            style={{ fontVariationSettings: "'FILL' 1" }}
          >
            biotech
          </span>
        </div>
        <div className="flex flex-col">
          <div className="flex items-center gap-2">
            <span className="font-sans text-lg font-bold text-primary-fixed tracking-tight">
              MedLearn AI
            </span>
            <span className="text-[10px] font-mono uppercase px-1.5 py-0.5 rounded bg-primary/20 text-primary-fixed border border-primary/30 font-semibold">
              v1.0 Atlas
            </span>
          </div>
          <span className="text-[11px] text-outline-variant hidden sm:inline-block">
            Multimodal Medical & Anatomy Study Companion
          </span>
        </div>
      </div>

      {/* Action Controls & Health */}
      <div className="flex items-center gap-3">
        {/* Backend Health Badge */}
        <div
          className={`flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium border transition-colors ${
            isBackendHealthy
              ? 'bg-success-clinical/10 text-success-clinical border-success-clinical/30'
              : 'bg-secondary-container/10 text-secondary-container border-secondary-container/30'
          }`}
          title={
            isBackendHealthy
              ? 'FastAPI Backend connected & healthy'
              : 'Checking FastAPI backend (http://localhost:8000)...'
          }
        >
          <span
            className={`w-2 h-2 rounded-full ${
              isBackendHealthy
                ? 'bg-success-clinical animate-pulse'
                : 'bg-secondary-container'
            }`}
          />
          <span className="font-mono text-[11px]">
            {isBackendHealthy ? 'API: Healthy' : 'API: Offline'}
          </span>
        </div>

        {/* Clear Chat */}
        <button
          onClick={onClearChat}
          className="p-2 rounded-full hover:bg-surface-subtle/10 transition-colors cursor-pointer active:scale-95 text-outline-variant hover:text-primary-fixed group"
          title="Reset conversation"
        >
          <span className="material-symbols-outlined text-[20px]">refresh</span>
        </button>

        {/* Info & OpenStax Attribution */}
        <a
          href="https://openstax.org/details/books/anatomy-and-physiology-2e"
          target="_blank"
          rel="noreferrer"
          className="p-2 rounded-full hover:bg-surface-subtle/10 transition-colors cursor-pointer active:scale-95 text-outline-variant hover:text-primary-fixed hidden sm:inline-flex"
          title="OpenStax Anatomy & Physiology 2e (CC BY 4.0)"
        >
          <span className="material-symbols-outlined text-[20px]">menu_book</span>
        </a>
      </div>
    </header>
  );
};
