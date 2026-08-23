export interface CitationModel {
  source: string;
  page: number;
  content_preview: string;
}

export interface EvaluationModel {
  grounded_score: number;
  is_faithful: boolean;
  reasoning: string;
}

export interface QuizOption {
  label: string;
  text: string;
}

export interface QuizQuestion {
  question: string;
  options: QuizOption[] | string[];
  correct_answer: string;
  explanation: string;
}

export interface AskResponse {
  question: string;
  answer: string;
  input_type: string;
  image_caption?: string | null;
  citations: CitationModel[];
  evaluation?: EvaluationModel | null;
  warning?: string | null;
  thread_id: string;
}

export interface QuizResponse {
  topic: string;
  questions: QuizQuestion[];
  thread_id: string;
}

export type PipelineStepStatus = 'idle' | 'running' | 'done' | 'error';

export interface PipelineStep {
  id: 'router' | 'captioner' | 'retriever' | 'explainer' | 'evaluator' | 'quiz_gen';
  label: string;
  icon: string;
  status: PipelineStepStatus;
}

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
  imageUrl?: string;
  imageCaption?: string;
  citations?: CitationModel[];
  evaluation?: EvaluationModel;
  quiz?: QuizQuestion[];
  steps?: PipelineStep[];
}

export interface AtlasDiagram {
  id: string;
  title: string;
  subtitle: string;
  description: string;
  imageUrl: string;
  tags: string[];
}
