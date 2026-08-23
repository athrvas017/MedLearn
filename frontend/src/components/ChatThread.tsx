import React from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { ChatMessage, CitationModel } from '../types';

interface ChatThreadProps {
  messages: ChatMessage[];
  isLoading: boolean;
  onSelectCitation?: (citation: CitationModel) => void;
  onStartQuiz?: () => void;
}

export const ChatThread: React.FC<ChatThreadProps> = ({
  messages,
  isLoading,
  onSelectCitation,
  onStartQuiz,
}) => {
  if (messages.length === 0 && !isLoading) {
    return (
      <div className="glass-panel rounded-2xl p-8 border border-outline-variant/20 flex flex-col items-center justify-center text-center gap-3 my-8 shadow-xl">
        <div className="w-14 h-14 rounded-2xl bg-primary/20 border border-primary/30 flex items-center justify-center glow-teal mb-1">
          <span
            className="material-symbols-outlined text-primary-fixed text-[32px]"
            style={{ fontVariationSettings: "'FILL' 1" }}
          >
            biotech
          </span>
        </div>
        <h3 className="text-lg font-bold text-primary-fixed">
          Welcome to MedLearn AI Interactive Atlas
        </h3>
        <p className="text-sm text-outline-variant max-w-md leading-relaxed">
          Ask any anatomy or physiology question, upload a histological diagram, or test your knowledge with interactive quizzes grounded in OpenStax textbook passages.
        </p>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-6">
      {messages.map((msg) => (
        <React.Fragment key={msg.id}>
          {msg.role === 'user' ? (
            /* User Query Message */
            <div className="flex gap-3 items-start w-full max-w-2xl ml-auto justify-end">
              <div className="glass rounded-2xl rounded-tr-sm p-4 bg-primary/10 border border-primary/20 shadow-md">
                {msg.imageUrl && (
                  <div className="mb-3 rounded-lg overflow-hidden border border-outline-variant/30 max-h-48">
                    <img
                      src={msg.imageUrl}
                      alt="Uploaded medical query"
                      className="w-full h-full object-cover"
                    />
                  </div>
                )}
                <p className="text-base text-surface-container-lowest leading-relaxed font-sans">
                  {msg.content}
                </p>
                <div className="mt-2 flex justify-end">
                  <span className="text-[10px] font-mono text-outline-variant">
                    {msg.timestamp}
                  </span>
                </div>
              </div>
              <div className="w-9 h-9 rounded-full bg-surface-variant/20 flex-shrink-0 flex items-center justify-center border border-outline-variant/20">
                <span className="material-symbols-outlined text-[20px] text-outline-variant">
                  person
                </span>
              </div>
            </div>
          ) : (
            /* AI Assistant Response Message */
            <div className="flex gap-3.5 items-start w-full max-w-3xl">
              <div className="w-9 h-9 rounded-full bg-primary/20 flex-shrink-0 flex items-center justify-center border border-primary/30 glow-teal mt-1">
                <span
                  className="material-symbols-outlined text-primary-fixed text-[20px]"
                  style={{ fontVariationSettings: "'FILL' 1" }}
                >
                  smart_toy
                </span>
              </div>

              <div className="glass-panel rounded-2xl rounded-tl-sm p-6 w-full flex flex-col gap-4 border border-outline/20 shadow-xl">
                {/* Header Badges */}
                <div className="flex items-center justify-between flex-wrap gap-2 border-b border-outline-variant/15 pb-3">
                  <div className="flex items-center gap-2">
                    {msg.evaluation ? (
                      <span
                        className={`px-2.5 py-1 rounded-full text-xs font-semibold flex items-center gap-1.5 border ${
                          msg.evaluation.is_faithful
                            ? 'bg-success-clinical/15 text-success-clinical border-success-clinical/30'
                            : 'bg-secondary-container/15 text-secondary-container border-secondary-container/30'
                        }`}
                        title={msg.evaluation.reasoning}
                      >
                        <span className="material-symbols-outlined text-[15px]">
                          {msg.evaluation.is_faithful ? 'verified' : 'warning'}
                        </span>
                        {msg.evaluation.is_faithful
                          ? `Grounded (${(msg.evaluation.grounded_score * 100).toFixed(0)}%)`
                          : 'Confidence Flagged'}
                      </span>
                    ) : (
                      <span className="px-2.5 py-1 rounded-full text-xs font-semibold bg-primary/15 text-primary-fixed border border-primary/30 flex items-center gap-1.5">
                        <span className="material-symbols-outlined text-[15px]">school</span>
                        MedLearn Response
                      </span>
                    )}

                    {msg.imageCaption && (
                      <span className="px-2 py-0.5 rounded bg-surface-variant/20 text-outline-variant text-[11px] font-mono border border-outline-variant/20 hidden sm:inline-flex items-center gap-1">
                        <span className="material-symbols-outlined text-[13px]">image</span>
                        {msg.imageCaption}
                      </span>
                    )}
                  </div>

                  <span className="text-[11px] font-mono text-outline-variant">
                    {msg.timestamp}
                  </span>
                </div>

                {/* Markdown Formatted Answer Body */}
                <div className="text-surface-subtle text-[15px] leading-relaxed font-sans space-y-3">
                  <ReactMarkdown
                    remarkPlugins={[remarkGfm]}
                    components={{
                      h1: ({ children }) => (
                        <h1 className="text-lg font-bold text-primary-fixed border-b border-outline-variant/20 pb-1.5 mt-3 mb-2">
                          {children}
                        </h1>
                      ),
                      h2: ({ children }) => (
                        <h2 className="text-base font-bold text-primary-fixed border-b border-outline-variant/15 pb-1 mt-3 mb-2">
                          {children}
                        </h2>
                      ),
                      h3: ({ children }) => (
                        <h3 className="text-[15px] font-bold text-primary-fixed mt-3 mb-1">
                          {children}
                        </h3>
                      ),
                      h4: ({ children }) => (
                        <h4 className="text-sm font-semibold text-primary-fixed mt-2 mb-1">
                          {children}
                        </h4>
                      ),
                      p: ({ children }) => (
                        <p className="leading-relaxed mb-2.5 text-surface-subtle">
                          {children}
                        </p>
                      ),
                      strong: ({ children }) => (
                        <strong className="font-semibold text-primary-fixed">
                          {children}
                        </strong>
                      ),
                      em: ({ children }) => (
                        <em className="text-surface-container-lowest font-medium not-italic">
                          {children}
                        </em>
                      ),
                      ul: ({ children }) => (
                        <ul className="list-disc pl-5 space-y-1.5 my-2 text-surface-subtle">
                          {children}
                        </ul>
                      ),
                      ol: ({ children }) => (
                        <ol className="list-decimal pl-5 space-y-1.5 my-2 text-surface-subtle">
                          {children}
                        </ol>
                      ),
                      li: ({ children }) => (
                        <li className="leading-relaxed pl-1 marker:text-primary-fixed">
                          {children}
                        </li>
                      ),
                      blockquote: ({ children }) => (
                        <blockquote className="border-l-2 border-primary pl-3 py-1 my-2 bg-primary/5 rounded-r text-sm text-outline-variant italic">
                          {children}
                        </blockquote>
                      ),
                      table: ({ children }) => (
                        <div className="overflow-x-auto my-3 rounded-lg border border-outline-variant/30">
                          <table className="min-w-full text-xs text-left">
                            {children}
                          </table>
                        </div>
                      ),
                      thead: ({ children }) => (
                        <thead className="bg-surface-variant/30 text-primary-fixed font-semibold">
                          {children}
                        </thead>
                      ),
                      tbody: ({ children }) => (
                        <tbody className="divide-y divide-outline-variant/20 bg-surface-variant/10">
                          {children}
                        </tbody>
                      ),
                      tr: ({ children }) => <tr>{children}</tr>,
                      th: ({ children }) => (
                        <th className="px-3 py-2 border-b border-outline-variant/30 font-semibold">
                          {children}
                        </th>
                      ),
                      td: ({ children }) => (
                        <td className="px-3 py-2 border-b border-outline-variant/10">
                          {children}
                        </td>
                      ),
                      code: ({ children }) => (
                        <code className="px-1.5 py-0.5 rounded bg-surface-variant/30 text-primary-fixed font-mono text-xs border border-outline-variant/30">
                          {children}
                        </code>
                      ),
                    }}
                  >
                    {msg.content}
                  </ReactMarkdown>
                </div>

                {/* Inline Citations Drawer */}
                {msg.citations && msg.citations.length > 0 && (
                  <div className="pt-3 border-t border-outline-variant/15 flex items-center gap-2 flex-wrap">
                    <span className="text-[11px] font-mono uppercase text-outline-variant font-semibold mr-1">
                      Textbook Citations:
                    </span>
                    {msg.citations.map((cit, cIdx) => (
                      <button
                        key={cIdx}
                        onClick={() => onSelectCitation && onSelectCitation(cit)}
                        className="px-2.5 py-1 rounded-md bg-primary/10 hover:bg-primary text-primary-fixed hover:text-on-primary border border-primary/30 text-xs font-mono transition-all flex items-center gap-1 cursor-pointer"
                        title={cit.content_preview}
                      >
                        <span className="material-symbols-outlined text-[13px]">book</span>
                        <span>[{cIdx + 1}]</span>
                        <span className="text-[11px] opacity-90 hidden sm:inline">
                          p.{cit.page}
                        </span>
                      </button>
                    ))}
                  </div>
                )}

                {/* Quiz CTA Banner if quiz questions exist */}
                {msg.quiz && msg.quiz.length > 0 && (
                  <div className="mt-2 p-3.5 rounded-xl bg-secondary-container/10 border border-secondary-container/30 flex items-center justify-between">
                    <div className="flex items-center gap-2.5">
                      <span className="material-symbols-outlined text-secondary-container text-[22px]">
                        quiz
                      </span>
                      <div>
                        <h6 className="text-xs font-bold text-secondary-container">
                          Interactive Quiz Ready ({msg.quiz.length} MCQs)
                        </h6>
                        <p className="text-[11px] text-outline-variant">
                          Test your comprehension in the Interactive Quiz tab.
                        </p>
                      </div>
                    </div>
                    <button
                      onClick={onStartQuiz}
                      className="px-3 py-1.5 rounded-lg bg-secondary-container/20 hover:bg-secondary-container text-secondary-container hover:text-on-secondary text-xs font-semibold transition-all border border-secondary-container/40 cursor-pointer"
                    >
                      Open Quiz
                    </button>
                  </div>
                )}
              </div>
            </div>
          )}
        </React.Fragment>
      ))}

      {/* Loading Skeleton */}
      {isLoading && (
        <div className="flex gap-3.5 items-start w-full max-w-3xl animate-pulse">
          <div className="w-9 h-9 rounded-full bg-primary/20 flex-shrink-0 flex items-center justify-center border border-primary/30 glow-teal">
            <span className="material-symbols-outlined text-primary-fixed text-[20px] animate-spin">
              autorenew
            </span>
          </div>
          <div className="glass-panel rounded-2xl rounded-tl-sm p-6 w-full flex flex-col gap-3 border border-outline/20">
            <div className="h-4 bg-primary/20 rounded w-1/3" />
            <div className="h-3.5 bg-surface-variant/20 rounded w-full" />
            <div className="h-3.5 bg-surface-variant/20 rounded w-5/6" />
            <div className="h-3.5 bg-surface-variant/20 rounded w-4/6" />
          </div>
        </div>
      )}
    </div>
  );
};
