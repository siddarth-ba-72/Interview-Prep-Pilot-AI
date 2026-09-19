import type { AxiosError } from 'axios'
import api from './axiosInstance'

export type ExperienceLevel = 'JUNIOR' | 'INTERMEDIATE' | 'SENIOR' | 'MASTER' | 'ADVANCED'
export type Difficulty = 'EASY' | 'MEDIUM' | 'HARD'
export type Rating = 'STRONG' | 'SATISFACTORY' | 'WEAK'

export interface InterviewConfig {
  experienceLevel: ExperienceLevel
  difficulty: Difficulty
  durationMinutes: number
}

export interface InterviewQuestion {
  question: string
  theme: string
  isFollowUp: boolean
}

export interface ThemeProgress {
  currentThemeIndex: number
  totalThemes: number
}

export interface InterviewExchange {
  index: number
  question: string
  theme: string
  isFollowUp: boolean
  userAnswer: string
  rating: Rating | null
  points: number | null
  feedback: string
}

export interface InterviewEvaluation {
  rating: Rating
  feedback: string
  points: number | null
}

export interface InterviewStartResponse {
  sessionId: string
  deadlineAt: string
  remainingSeconds: number
  currentQuestion: InterviewQuestion | null
  themeProgress: ThemeProgress
  status: string
  config: InterviewConfig
  exchanges: InterviewExchange[]
  resumed: boolean
}

export interface InterviewStateResponse {
  isComplete: boolean
  sessionId: string
  status: string
  deadlineAt: string
  remainingSeconds: number
  currentQuestion: InterviewQuestion | null
  themeProgress: ThemeProgress
  exchanges: InterviewExchange[]
  completionReason: string | null
  config: InterviewConfig
  report: InterviewReportResponse | null
}

export interface InterviewAnswerResponse {
  evaluation: InterviewEvaluation | null
  nextQuestion: InterviewQuestion | null
  themeProgress: ThemeProgress
  exchange: InterviewExchange | null
  remainingSeconds: number
  isComplete: boolean
}

export interface InterviewReportResponse {
  sessionId: string
  score: number
  maxScore: number
  passThreshold: number
  passed: boolean
  strengths: string[]
  weaknesses: string[]
  improvementSuggestions: Array<{
    question: string
    userAnswer: string | null
    theme: string | null
    betterAnswer: string
  }>
  overallSummary: string
  config: InterviewConfig | null
  completionReason: string | null
  exchangeSummary: InterviewExchange[]
  createdAt: string
}

/** A row in the interview history list. Reports are generated lazily, so `score`, `maxScore`
 * and `passed` stay null for an interview whose report has never been opened. */
export interface InterviewSummary {
  sessionId: string
  status: 'IN_PROGRESS' | 'COMPLETED'
  completionReason: string | null
  config: InterviewConfig
  score: number | null
  maxScore: number | null
  passed: boolean | null
  answeredCount: number
  createdAt: string
  completedAt: string | null
}

/** Surfaces the API's `{ error: { code, message } }` body instead of Axios's
 * generic "Request failed with status code 500". */
export function interviewErrorMessage(error: unknown, fallback: string): string {
  const axiosError = error as AxiosError<{ error?: { message?: string } }>
  const apiMessage = axiosError?.response?.data?.error?.message
  if (apiMessage) return apiMessage
  if (error instanceof Error && error.message) return error.message
  return fallback
}

export async function startInterview(topicId: string, config: InterviewConfig): Promise<InterviewStartResponse> {
  const { data } = await api.post<InterviewStartResponse>(`/topics/${topicId}/interviews`, config)
  return data
}

export async function getInterview(topicId: string, sessionId: string): Promise<InterviewStateResponse> {
  const { data } = await api.get<InterviewStateResponse>(`/topics/${topicId}/interviews/${sessionId}`)
  return data
}

export async function listInterviews(topicId: string): Promise<InterviewSummary[]> {
  const { data } = await api.get<InterviewSummary[]>(`/topics/${topicId}/interviews`)
  return data
}

export async function answerInterview(topicId: string, sessionId: string, answer: string): Promise<InterviewAnswerResponse> {
  const { data } = await api.post<InterviewAnswerResponse>(`/topics/${topicId}/interviews/${sessionId}/answer`, { answer })
  return data
}

export async function endInterview(topicId: string, sessionId: string): Promise<InterviewReportResponse> {
  const { data } = await api.post<InterviewReportResponse>(`/topics/${topicId}/interviews/${sessionId}/end`)
  return data
}

export async function getInterviewReport(topicId: string, sessionId: string): Promise<InterviewReportResponse> {
  const { data } = await api.get<InterviewReportResponse>(`/topics/${topicId}/interviews/${sessionId}/report`)
  return data
}
