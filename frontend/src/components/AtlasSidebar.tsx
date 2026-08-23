import React, { useState } from 'react';
import { CitationModel, QuizQuestion } from '../types';

interface AtlasSidebarProps {
  activeTab: 'atlas' | 'quiz';
  setActiveTab: (tab: 'atlas' | 'quiz') => void;
  citations: CitationModel[];
  selectedCitation: CitationModel | null;
  quizQuestions: QuizQuestion[];
  onGenerateQuizTopic: (topic: string) => void;
  isGeneratingQuiz: boolean;
}

export const AtlasSidebar: React.FC<AtlasSidebarProps> = ({
  activeTab,
  setActiveTab,
  citations,
  selectedCitation,
  quizQuestions,
  onGenerateQuizTopic,
  isGeneratingQuiz,
}) => {
  const [selectedAnswers, setSelectedAnswers] = useState<Record<number, string>>({});
  const [showExplanations, setShowExplanations] = useState<Record<number, boolean>>({});
  const [isFullscreenModalOpen, setIsFullscreenModalOpen] = useState(false);

  const handleSelectOption = (qIdx: number, label: string) => {
    if (selectedAnswers[qIdx] !== undefined) return; // already answered
    setSelectedAnswers((prev) => ({ ...prev, [qIdx]: label }));
    setShowExplanations((prev) => ({ ...prev, [qIdx]: true }));
  };

  const calculateScore = () => {
    if (quizQuestions.length === 0) return { correct: 0, total: 0 };
    let correct = 0;
    quizQuestions.forEach((q, idx) => {
      if (selectedAnswers[idx] === q.correct_answer) {
        correct++;
      }
    });
    return { correct, total: quizQuestions.length };
  };

  const resetQuiz = () => {
    setSelectedAnswers({});
    setShowExplanations({});
  };

  const defaultAtlasImage =
    'https://images.unsplash.com/photo-1530497610245-94d3c16cda28?auto=format&fit=crop&w=900&q=80';

  return (
    <aside className="w-full md:w-[380px] lg:w-[420px] border-l border-outline/30 bg-inverse-surface/60 backdrop-blur-md flex flex-col h-full animate-slide-in flex-shrink-0">
      {/* Tab Navigation */}
      <div className="flex border-b border-outline/30 bg-inverse-surface/80">
        <button
          onClick={() => setActiveTab('atlas')}
          className={`flex-1 py-3.5 text-xs font-semibold uppercase tracking-wider transition-all flex items-center justify-center gap-2 cursor-pointer ${
            activeTab === 'atlas'
              ? 'text-primary-fixed border-b-2 border-primary-fixed bg-surface-variant/10'
              : 'text-outline-variant hover:text-surface-subtle'
          }`}
        >
          <span className="material-symbols-outlined text-[18px]">menu_book</span>
          Source Atlas
        </button>
        <button
          onClick={() => setActiveTab('quiz')}
          className={`flex-1 py-3.5 text-xs font-semibold uppercase tracking-wider transition-all flex items-center justify-center gap-2 cursor-pointer ${
            activeTab === 'quiz'
              ? 'text-primary-fixed border-b-2 border-primary-fixed bg-surface-variant/10'
              : 'text-outline-variant hover:text-surface-subtle'
          }`}
        >
          <span className="material-symbols-outlined text-[18px]">quiz</span>
          Interactive Quiz
          {quizQuestions.length > 0 && (
            <span className="w-5 h-5 rounded-full bg-secondary-container text-on-secondary-fixed text-[10px] font-mono flex items-center justify-center font-bold">
              {quizQuestions.length}
            </span>
          )}
        </button>
      </div>

      {/* Content Area */}
      <div className="flex-1 overflow-y-auto p-4 flex flex-col gap-4">
        {activeTab === 'atlas' ? (
          /* =================================================================== */
          /* SOURCE ATLAS TAB                                                   */
          /* =================================================================== */
          <div className="flex flex-col gap-4">
            {/* Atlas Visualization Card */}
            <div className="glass-panel rounded-2xl overflow-hidden flex flex-col border border-primary/25 shadow-xl">
              <div className="relative h-48 w-full bg-on-background group">
                <div
                  className="absolute inset-0 bg-cover bg-center opacity-85 group-hover:scale-105 transition-transform duration-500"
                  style={{ backgroundImage: `url('${defaultAtlasImage}')` }}
                />
                <div className="absolute inset-0 bg-gradient-to-t from-inverse-surface via-inverse-surface/30 to-transparent" />
                <div className="absolute bottom-2.5 left-3.5 right-3.5 flex justify-between items-end">
                  <div>
                    <span className="text-xs font-bold text-primary-fixed block drop-shadow-md">
                      Interactive Atlas Plate
                    </span>
                    <span className="text-sm font-bold text-surface-container-lowest drop-shadow-md">
                      Ventricular Action Potential & Ion Permeability
                    </span>
                  </div>
                  <button
                    onClick={() => setIsFullscreenModalOpen(true)}
                    className="w-8 h-8 rounded-full bg-primary/80 backdrop-blur-sm flex items-center justify-center text-on-primary hover:bg-primary transition-all cursor-pointer shadow-lg"
                    title="Fullscreen preview"
                  >
                    <span className="material-symbols-outlined text-[18px]">fullscreen</span>
                  </button>
                </div>
              </div>

              <div className="p-4 bg-inverse-surface/80 border-t border-outline-variant/15">
                <p className="text-xs text-outline-variant leading-relaxed mb-3">
                  Correlation between membrane potential (mV) and time (ms) alongside rapid Na⁺ influx, Ca²⁺ plateau kinetics, and delayed rectifier K⁺ repolarization.
                </p>
                <div className="flex gap-2 flex-wrap">
                  <span className="px-2 py-0.5 rounded bg-surface-variant/20 border border-outline-variant/30 font-mono text-[11px] text-primary-fixed">
                    INa (Phase 0)
                  </span>
                  <span className="px-2 py-0.5 rounded bg-surface-variant/20 border border-outline-variant/30 font-mono text-[11px] text-primary-fixed">
                    ICa,L (Phase 2)
                  </span>
                  <span className="px-2 py-0.5 rounded bg-surface-variant/20 border border-outline-variant/30 font-mono text-[11px] text-primary-fixed">
                    IK1 (Phase 3)
                  </span>
                </div>
              </div>
            </div>

            {/* Retrieved Textbook Citations Section */}
            <div className="flex flex-col gap-2.5">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold text-surface-subtle flex items-center gap-1.5">
                  <span className="material-symbols-outlined text-[16px] text-primary-fixed">
                    menu_book
                  </span>
                  OpenStax Textbook Passages ({citations.length})
                </span>
                <span className="text-[10px] font-mono text-outline-variant">
                  ChromaDB top-k
                </span>
              </div>

              {citations.length === 0 ? (
                <div className="p-4 rounded-xl glass border border-outline-variant/20 text-center text-outline-variant text-xs">
                  Ask a question to retrieve passages from OpenStax Anatomy & Physiology 2e.
                </div>
              ) : (
                citations.map((cit, idx) => {
                  const isHighlighted = selectedCitation === cit;
                  return (
                    <div
                      key={idx}
                      className={`p-3.5 rounded-xl border transition-all ${
                        isHighlighted
                          ? 'glass-panel border-primary-fixed bg-primary/10 ring-2 ring-primary/20 shadow-lg'
                          : 'glass border-outline-variant/20 hover:border-primary/40'
                      }`}
                    >
                      <div className="flex items-center justify-between mb-1.5">
                        <span className="text-xs font-bold text-primary-fixed flex items-center gap-1">
                          <span className="w-4 h-4 rounded-full bg-primary/20 flex items-center justify-center text-[10px] font-mono font-bold">
                            {idx + 1}
                          </span>
                          {cit.source}
                        </span>
                        <span className="text-[11px] font-mono text-outline-variant px-1.5 py-0.5 rounded bg-surface-variant/20 border border-outline-variant/30">
                          Page {cit.page}
                        </span>
                      </div>
                      <p className="text-xs text-outline-variant leading-relaxed font-sans line-clamp-4 hover:line-clamp-none transition-all">
                        "{cit.content_preview}"
                      </p>
                    </div>
                  );
                })
              )}
            </div>
          </div>
        ) : (
          /* =================================================================== */
          /* INTERACTIVE QUIZ TAB                                                */
          /* =================================================================== */
          <div className="flex flex-col gap-4">
            {quizQuestions.length === 0 ? (
              /* Empty Quiz State */
              <div className="border border-secondary-container/30 rounded-2xl p-5 bg-secondary-container/5 relative overflow-hidden group">
                <div className="flex items-center gap-2 mb-2 text-secondary-container">
                  <span className="material-symbols-outlined text-[24px]">quiz</span>
                  <h4 className="text-sm font-bold">Knowledge Check Generator</h4>
                </div>
                <p className="text-xs text-outline-variant mb-4 leading-relaxed">
                  Generate instant 3-question MCQ assessments based on the current medical topic to test active recall.
                </p>
                <button
                  onClick={() => onGenerateQuizTopic('Cardiac Action Potential and Myocardial Cells')}
                  disabled={isGeneratingQuiz}
                  className="w-full py-2.5 rounded-xl bg-secondary-container/20 hover:bg-secondary-container text-secondary-container hover:text-on-secondary text-xs font-bold border border-secondary-container/40 transition-all flex items-center justify-center gap-2 cursor-pointer shadow-md"
                >
                  {isGeneratingQuiz ? (
                    <>
                      <span className="material-symbols-outlined text-[16px] animate-spin">
                        autorenew
                      </span>
                      Synthesizing Quiz...
                    </>
                  ) : (
                    <>
                      <span className="material-symbols-outlined text-[16px]">play_arrow</span>
                      Start 3-Question Practice Quiz
                    </>
                  )}
                </button>
              </div>
            ) : (
              /* Active Quiz Questions Runner */
              <div className="flex flex-col gap-5">
                {/* Score Summary Header */}
                <div className="glass rounded-xl p-3 border border-secondary-container/30 flex items-center justify-between bg-secondary-container/10">
                  <div className="flex items-center gap-2">
                    <span className="material-symbols-outlined text-secondary-container text-[20px]">
                      military_tech
                    </span>
                    <span className="text-xs font-bold text-secondary-container">
                      Score: {calculateScore().correct} / {calculateScore().total} Completed
                    </span>
                  </div>
                  <button
                    onClick={resetQuiz}
                    className="text-[11px] font-mono text-outline-variant hover:text-primary-fixed underline cursor-pointer"
                  >
                    Reset Answers
                  </button>
                </div>

                {/* Question Cards */}
                {quizQuestions.map((q, qIdx) => {
                  const userAnswer = selectedAnswers[qIdx];
                  const hasAnswered = userAnswer !== undefined;
                  const isCorrect = userAnswer === q.correct_answer;

                  // Normalize options
                  const optionsList = Array.isArray(q.options)
                    ? q.options.map((opt) => {
                        if (typeof opt === 'string') {
                          const match = opt.match(/^([A-D])\)\s*(.*)$/);
                          return match
                            ? { label: match[1], text: match[2] }
                            : { label: opt.slice(0, 1), text: opt };
                        }
                        return opt;
                      })
                    : [];

                  return (
                    <div
                      key={qIdx}
                      className="glass-panel rounded-2xl p-4 border border-outline-variant/20 flex flex-col gap-3 shadow-lg"
                    >
                      <div className="flex items-start gap-2">
                        <span className="w-5 h-5 rounded-full bg-secondary-container/20 text-secondary-container text-xs font-mono font-bold flex items-center justify-center flex-shrink-0 mt-0.5">
                          {qIdx + 1}
                        </span>
                        <h5 className="text-xs font-bold text-surface-container-lowest leading-snug">
                          {q.question}
                        </h5>
                      </div>

                      {/* Options Grid */}
                      <div className="flex flex-col gap-2 mt-1">
                        {optionsList.map((opt) => {
                          const isThisSelected = userAnswer === opt.label;
                          const isThisCorrect = opt.label === q.correct_answer;

                          let optionStyle =
                            'bg-surface-variant/10 border-outline-variant/20 hover:border-primary/50 text-surface-subtle';
                          if (hasAnswered) {
                            if (isThisCorrect) {
                              optionStyle =
                                'bg-success-clinical/15 border-success-clinical/50 text-success-clinical font-semibold';
                            } else if (isThisSelected && !isThisCorrect) {
                              optionStyle =
                                'bg-danger-crimson/15 border-danger-crimson/50 text-danger-crimson font-semibold';
                            } else {
                              optionStyle = 'opacity-50 border-outline-variant/10 text-outline-variant';
                            }
                          }

                          return (
                            <button
                              key={opt.label}
                              onClick={() => handleSelectOption(qIdx, opt.label)}
                              disabled={hasAnswered}
                              className={`p-2.5 rounded-xl border text-left text-xs transition-all flex items-center gap-2.5 cursor-pointer ${optionStyle}`}
                            >
                              <span className="w-5 h-5 rounded-md bg-surface-variant/30 flex items-center justify-center font-mono font-bold text-[11px] flex-shrink-0">
                                {opt.label}
                              </span>
                              <span className="flex-1 font-sans">{opt.text}</span>
                              {hasAnswered && isThisCorrect && (
                                <span className="material-symbols-outlined text-[16px] text-success-clinical">
                                  check_circle
                                </span>
                              )}
                              {hasAnswered && isThisSelected && !isThisCorrect && (
                                <span className="material-symbols-outlined text-[16px] text-danger-crimson">
                                  cancel
                                </span>
                              )}
                            </button>
                          );
                        })}
                      </div>

                      {/* Feedback / Explanation Box */}
                      {showExplanations[qIdx] && (
                        <div
                          className={`p-3 rounded-xl border text-xs leading-relaxed mt-1 animate-slide-in ${
                            isCorrect
                              ? 'bg-success-clinical/10 border-success-clinical/30 text-success-clinical'
                              : 'bg-danger-crimson/10 border-danger-crimson/30 text-danger-crimson'
                          }`}
                        >
                          <div className="font-bold mb-1 flex items-center gap-1">
                            <span className="material-symbols-outlined text-[14px]">
                              {isCorrect ? 'check' : 'error'}
                            </span>
                            {isCorrect
                              ? 'Correct!'
                              : `Incorrect (Correct answer is ${q.correct_answer})`}
                          </div>
                          <p className="text-[11px] text-surface-subtle opacity-90 font-sans">
                            {q.explanation}
                          </p>
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Fullscreen Atlas Modal */}
      {isFullscreenModalOpen && (
        <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-md flex items-center justify-center p-4">
          <div className="glass-panel max-w-4xl w-full rounded-2xl p-6 border border-primary/40 flex flex-col gap-4 relative shadow-2xl">
            <div className="flex justify-between items-center border-b border-outline-variant/20 pb-3">
              <h3 className="text-base font-bold text-primary-fixed">
                High-Resolution Atlas: Ventricular Myocyte Action Potential
              </h3>
              <button
                onClick={() => setIsFullscreenModalOpen(false)}
                className="p-1.5 rounded-full hover:bg-surface-variant/30 text-outline-variant hover:text-surface-container-lowest"
              >
                <span className="material-symbols-outlined text-[20px]">close</span>
              </button>
            </div>
            <div className="w-full h-[60vh] rounded-xl overflow-hidden border border-outline-variant/30 bg-black">
              <img
                src={defaultAtlasImage}
                alt="Atlas High Res"
                className="w-full h-full object-contain"
              />
            </div>
            <div className="text-xs text-outline-variant font-mono flex justify-between">
              <span>Source: OpenStax Anatomy & Physiology 2e (CC BY 4.0)</span>
              <span>Zoom 100%</span>
            </div>
          </div>
        </div>
      )}
    </aside>
  );
};
