import type { ReviewRecord } from "./progress";
export interface CloudReview extends ReviewRecord {
  version: number;
}
export interface DashboardData {
  lessons: { slug: string; title: string; progress: number; version: number }[];
  cards: Record<string, CloudReview>;
  due_count: number;
  quiz: {
    graded: number;
    correct: number;
    pending: number;
    recent: {
      id?: string;
      question_key: string;
      correct: boolean | null;
      status: string;
      created_at: string;
      prompt?: string;
      answer?: string;
      expected?: string;
      explanation?: string;
      selection_explanation?: string;
    }[];
  };
}
export interface Question {
  key: string;
  prompt: string;
  question_type: string;
  options: { text: string }[];
  manual: boolean;
}
export interface LearningLesson {
  slug: string;
  title: string;
  private_development: boolean;
}
