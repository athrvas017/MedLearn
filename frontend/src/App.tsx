import { useState, useEffect } from 'react';
import { TopAppBar } from './components/TopAppBar';
import { PipelineStepper } from './components/PipelineStepper';
import { ChatThread } from './components/ChatThread';
import { InputBar } from './components/InputBar';
import { AtlasSidebar } from './components/AtlasSidebar';
import { MobileBottomNav } from './components/MobileBottomNav';
import { apiService } from './services/api';
import {
  ChatMessage,
  CitationModel,
  PipelineStep,
  QuizQuestion,
} from './types';

export function App() {
  const [isBackendHealthy, setIsBackendHealthy] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [isGeneratingQuiz, setIsGeneratingQuiz] = useState(false);
  const [activeSidebarTab, setActiveSidebarTab] = useState<'atlas' | 'quiz'>('atlas');
  const [activeMobileTab, setActiveMobileTab] = useState('chat');
  const [selectedCitation, setSelectedCitation] = useState<CitationModel | null>(null);

  // Dynamic Pipeline Steps
  const [steps, setSteps] = useState<PipelineStep[]>([
    { id: 'router', label: 'Router', icon: 'route', status: 'idle' },
    { id: 'captioner', label: 'Captioner', icon: 'image', status: 'idle' },
    { id: 'retriever', label: 'Retriever', icon: 'search', status: 'idle' },
    { id: 'explainer', label: 'Synthesizer', icon: 'psychology', status: 'idle' },
    { id: 'evaluator', label: 'Evaluator', icon: 'verified', status: 'idle' },
  ]);

  // Messages initialized clean (no hardcoded simulations)
  const [messages, setMessages] = useState<ChatMessage[]>([]);

  // Citations & Quiz Questions for right sidebar from the latest message
  const currentCitations: CitationModel[] =
    messages[messages.length - 1]?.citations || [];
  const currentQuizQuestions: QuizQuestion[] =
    messages[messages.length - 1]?.quiz || [];

  // Poll backend health
  useEffect(() => {
    const check = async () => {
      const healthy = await apiService.checkHealth();
      setIsBackendHealthy(healthy);
    };
    check();
    const interval = setInterval(check, 10000);
    return () => clearInterval(interval);
  }, []);

  // Handle Send Question
  const handleSend = async (
    queryText: string,
    imageFile?: File | null,
    generateQuiz: boolean = false
  ) => {
    const userMsgId = `usr-${Date.now()}`;
    const timestamp = new Date().toLocaleTimeString([], {
      hour: '2-digit',
      minute: '2-digit',
    });

    const userMessage: ChatMessage = {
      id: userMsgId,
      role: 'user',
      content: queryText,
      timestamp,
      imageUrl: imageFile ? URL.createObjectURL(imageFile) : undefined,
    };

    setMessages((prev) => [...prev, userMessage]);
    setIsLoading(true);

    // Update Stepper to running
    setSteps([
      { id: 'router', label: 'Router', icon: 'route', status: 'running' },
      { id: 'captioner', label: 'Captioner', icon: 'image', status: imageFile ? 'running' : 'idle' },
      { id: 'retriever', label: 'Retriever', icon: 'search', status: 'running' },
      { id: 'explainer', label: 'Synthesizer', icon: 'psychology', status: 'running' },
      { id: 'evaluator', label: 'Evaluator', icon: 'verified', status: 'running' },
    ]);

    try {
      // Call live FastAPI Backend API
      const response = await apiService.askQuestion(queryText, imageFile, generateQuiz);

      // Set Stepper to done
      setSteps([
        { id: 'router', label: 'Router', icon: 'route', status: 'done' },
        { id: 'captioner', label: 'Captioner', icon: 'image', status: imageFile ? 'done' : 'idle' },
        { id: 'retriever', label: 'Retriever', icon: 'search', status: 'done' },
        { id: 'explainer', label: 'Synthesizer', icon: 'psychology', status: 'done' },
        { id: 'evaluator', label: 'Evaluator', icon: 'verified', status: 'done' },
      ]);

      // Fetch quiz questions if requested
      let generatedQuiz: QuizQuestion[] | undefined = undefined;
      if (generateQuiz) {
        try {
          const quizRes = await apiService.generateQuiz(queryText, 3);
          generatedQuiz = quizRes.questions;
        } catch (quizErr) {
          console.error('Quiz generation failed:', quizErr);
        }
      }

      const assistantMessage: ChatMessage = {
        id: `ai-${Date.now()}`,
        role: 'assistant',
        content: response.answer,
        timestamp: new Date().toLocaleTimeString([], {
          hour: '2-digit',
          minute: '2-digit',
        }),
        imageCaption: response.image_caption || undefined,
        citations: response.citations || [],
        evaluation: response.evaluation || undefined,
        quiz: generatedQuiz,
      };

      setMessages((prev) => [...prev, assistantMessage]);
    } catch (err: any) {
      console.error('MedLearn API Request Error:', err);

      setSteps((prev) =>
        prev.map((s) => ({
          ...s,
          status: 'error',
        }))
      );

      const errorDetail =
        err?.response?.data?.detail ||
        err?.message ||
        'Failed to connect to backend server';

      const errorMessage: ChatMessage = {
        id: `err-${Date.now()}`,
        role: 'assistant',
        content: `⚠️ **API Error**: ${errorDetail}\n\nPlease verify that the FastAPI backend server is running on port 8000 and check the console logs.`,
        timestamp: new Date().toLocaleTimeString([], {
          hour: '2-digit',
          minute: '2-digit',
        }),
      };

      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  // Generate Practice Quiz on Demand
  const handleGenerateQuizTopic = async (topic: string) => {
    setIsGeneratingQuiz(true);
    try {
      const res = await apiService.generateQuiz(topic, 3);
      if (res && res.questions) {
        setMessages((prev) => {
          const last = prev[prev.length - 1];
          if (last && last.role === 'assistant') {
            return [
              ...prev.slice(0, -1),
              {
                ...last,
                quiz: res.questions,
              },
            ];
          }
          return prev;
        });
        setActiveSidebarTab('quiz');
      }
    } catch (err) {
      console.error('Quiz generation error:', err);
    } finally {
      setIsGeneratingQuiz(false);
    }
  };

  const handleClearChat = () => {
    setMessages([]);
    setSteps([
      { id: 'router', label: 'Router', icon: 'route', status: 'idle' },
      { id: 'captioner', label: 'Captioner', icon: 'image', status: 'idle' },
      { id: 'retriever', label: 'Retriever', icon: 'search', status: 'idle' },
      { id: 'explainer', label: 'Synthesizer', icon: 'psychology', status: 'idle' },
      { id: 'evaluator', label: 'Evaluator', icon: 'verified', status: 'idle' },
    ]);
  };

  return (
    <div className="bg-on-surface text-surface-subtle font-sans h-screen overflow-hidden flex flex-col antialiased">
      {/* Top Application Bar */}
      <TopAppBar
        isBackendHealthy={isBackendHealthy}
        onClearChat={handleClearChat}
        activeMobileTab={activeMobileTab}
        setActiveMobileTab={setActiveMobileTab}
      />

      {/* Main Workspace Layout */}
      <main className="flex-1 flex pt-16 h-full overflow-hidden">
        {/* Left Column: Interactive Chat Thread & Pipeline */}
        <section
          className={`flex-1 flex flex-col h-full overflow-y-auto relative pb-28 md:pb-6 ${
            activeMobileTab !== 'chat' ? 'hidden md:flex' : 'flex'
          }`}
        >
          <div className="max-w-container-max mx-auto w-full p-4 md:p-6 flex flex-col gap-5">
            {/* Agent Pipeline Stepper */}
            <PipelineStepper steps={steps} />

            {/* Chat Thread */}
            <ChatThread
              messages={messages}
              isLoading={isLoading}
              onSelectCitation={(cit) => {
                setSelectedCitation(cit);
                setActiveSidebarTab('atlas');
              }}
              onStartQuiz={() => setActiveSidebarTab('quiz')}
            />
          </div>

          {/* Sticky Input Bar at Bottom of Left Column */}
          <div className="sticky bottom-0 w-full max-w-container-max mx-auto px-4 md:px-6 pb-4 pt-2 bg-gradient-to-t from-on-surface via-on-surface/90 to-transparent">
            <InputBar onSend={handleSend} isLoading={isLoading} />
          </div>
        </section>

        {/* Right Sidebar: Source Atlas & Interactive Quiz */}
        <div
          className={`h-full ${
            activeMobileTab === 'sources' || activeMobileTab === 'quiz'
              ? 'flex w-full md:w-auto'
              : 'hidden md:flex'
          }`}
        >
          <AtlasSidebar
            activeTab={activeSidebarTab}
            setActiveTab={setActiveSidebarTab}
            citations={currentCitations}
            selectedCitation={selectedCitation}
            quizQuestions={currentQuizQuestions}
            onGenerateQuizTopic={handleGenerateQuizTopic}
            isGeneratingQuiz={isGeneratingQuiz}
          />
        </div>
      </main>

      {/* Bottom Navigation for Mobile */}
      <MobileBottomNav
        activeMobileTab={activeMobileTab}
        setActiveMobileTab={setActiveMobileTab}
        onOpenAtlasTab={(tab) => {
          setActiveSidebarTab(tab);
        }}
      />
    </div>
  );
}

export default App;
