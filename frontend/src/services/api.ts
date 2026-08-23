import axios from 'axios';
import { AskResponse, QuizResponse } from '../types';

// Use relative URL so Vite proxy forwards to http://localhost:8000 seamlessly
const API_BASE = '';

const client = axios.create({
  baseURL: API_BASE,
  timeout: 120000,
});

export const apiService = {
  async checkHealth(): Promise<boolean> {
    try {
      const res = await client.get('/health');
      return res.status === 200 && res.data.status === 'healthy';
    } catch (err) {
      console.error('Health check error:', err);
      return false;
    }
  },

  async askQuestion(
    query: string,
    imageFile?: File | null,
    generateQuiz: boolean = false
  ): Promise<AskResponse> {
    const formData = new FormData();
    formData.append('query', query);
    if (imageFile) {
      formData.append('image', imageFile);
    }
    if (generateQuiz) {
      formData.append('generate_quiz', 'true');
    }

    try {
      const res = await client.post<AskResponse>('/api/v1/ask', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });
      return res.data;
    } catch (err) {
      console.error('askQuestion API error:', err);
      throw err;
    }
  },

  async generateQuiz(topic: string, numQuestions: number = 3): Promise<QuizResponse> {
    const formData = new FormData();
    formData.append('topic', topic);
    formData.append('num_questions', String(numQuestions));

    try {
      const res = await client.post<QuizResponse>('/api/v1/quiz', formData);
      return res.data;
    } catch (err) {
      console.error('generateQuiz API error:', err);
      throw err;
    }
  },
};
