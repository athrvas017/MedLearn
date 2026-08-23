import React from 'react';

interface MobileBottomNavProps {
  activeMobileTab: string;
  setActiveMobileTab: (tab: string) => void;
  onOpenAtlasTab: (tab: 'atlas' | 'quiz') => void;
}

export const MobileBottomNav: React.FC<MobileBottomNavProps> = ({
  activeMobileTab,
  setActiveMobileTab,
  onOpenAtlasTab,
}) => {
  return (
    <nav className="md:hidden fixed bottom-0 left-0 w-full flex justify-around items-center h-16 bg-inverse-surface/95 border-t border-outline-variant/20 z-50 glass backdrop-blur-lg">
      {/* Chat Tab */}
      <button
        onClick={() => setActiveMobileTab('chat')}
        className={`flex flex-col items-center justify-center p-2 transition-all ${
          activeMobileTab === 'chat'
            ? 'text-primary-fixed font-bold scale-105'
            : 'text-on-surface-variant hover:text-primary-fixed'
        }`}
      >
        <span
          className="material-symbols-outlined mb-1 text-[20px]"
          style={activeMobileTab === 'chat' ? { fontVariationSettings: "'FILL' 1" } : {}}
        >
          chat_bubble
        </span>
        <span className="text-[10px] font-sans">Chat</span>
      </button>

      {/* Sources Tab */}
      <button
        onClick={() => {
          setActiveMobileTab('sources');
          onOpenAtlasTab('atlas');
        }}
        className={`flex flex-col items-center justify-center p-2 transition-all ${
          activeMobileTab === 'sources'
            ? 'text-primary-fixed font-bold scale-105'
            : 'text-on-surface-variant hover:text-primary-fixed'
        }`}
      >
        <span
          className="material-symbols-outlined mb-1 text-[20px]"
          style={activeMobileTab === 'sources' ? { fontVariationSettings: "'FILL' 1" } : {}}
        >
          menu_book
        </span>
        <span className="text-[10px] font-sans">Sources</span>
      </button>

      {/* Quiz Tab */}
      <button
        onClick={() => {
          setActiveMobileTab('quiz');
          onOpenAtlasTab('quiz');
        }}
        className={`flex flex-col items-center justify-center p-2 transition-all ${
          activeMobileTab === 'quiz'
            ? 'text-primary-fixed font-bold scale-105'
            : 'text-on-surface-variant hover:text-primary-fixed'
        }`}
      >
        <span
          className="material-symbols-outlined mb-1 text-[20px]"
          style={activeMobileTab === 'quiz' ? { fontVariationSettings: "'FILL' 1" } : {}}
        >
          quiz
        </span>
        <span className="text-[10px] font-sans">Quiz</span>
      </button>

      {/* OpenStax Library Tab */}
      <a
        href="https://openstax.org/details/books/anatomy-and-physiology-2e"
        target="_blank"
        rel="noreferrer"
        className="flex flex-col items-center justify-center text-on-surface-variant p-2 hover:text-primary-fixed transition-all"
      >
        <span className="material-symbols-outlined mb-1 text-[20px]">
          folder_open
        </span>
        <span className="text-[10px] font-sans">Library</span>
      </a>
    </nav>
  );
};
