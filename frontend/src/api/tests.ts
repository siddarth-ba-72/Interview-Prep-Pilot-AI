import api from './axiosInstance'

export interface TestQuestion {
  questionId: string
  section: 'MCQ' | 'SUBJECTIVE'
  text: string
  options?: string[] | null
}

export interface TestSessionStartResponse {
  sessionId: string
  questions: TestQuestion[]
}

export interface SubmitAnswerRequest {
  questionId: string
  userAnswer: string | null
}

export interface SubmitTestRequest {
  answers: SubmitAnswerRequest[]
}

export interface QuestionResult {
  questionId: string
  section: string
  questionText: string
  userAnswer: string | null
  correctAnswer: string
  isCorrect: boolean
  evaluation: string
  pointsAwarded: number
}

export interface TestReportResponse {
  testSessionId: string
  rawScore: number
  maxScore: number
  passThreshold: number
  passed: boolean
  avgScoreAtTime: number
  strengths: string[]
  weaknesses: string[]
  questionSummary: QuestionResult[]
  createdAt: string
}

export interface TestSessionListItem {
  sessionId: string
  completedAt: string
  rawScore: number
}

// Test API functions

export async function startTest(topicId: string): Promise<TestSessionStartResponse> {
  const { data } = await api.post<TestSessionStartResponse>(`/topics/${topicId}/tests`)
  return data
}

export async function getTest(topicId: string, testId: string): Promise<TestSessionStartResponse> {
  const { data } = await api.get<TestSessionStartResponse>(`/topics/${topicId}/tests/${testId}`)
  return data
}

export async function submitTest(
  topicId: string,
  testId: string,
  request: SubmitTestRequest
): Promise<TestReportResponse> {
  const { data } = await api.post<TestReportResponse>(
    `/topics/${topicId}/tests/${testId}/submit`,
    request
  )
  return data
}

export async function getTestReport(topicId: string, testId: string): Promise<TestReportResponse> {
  const { data } = await api.get<TestReportResponse>(`/topics/${topicId}/tests/${testId}/report`)
  return data
}

export async function listTestSessions(topicId: string): Promise<TestSessionListItem[]> {
  const { data } = await api.get<TestSessionListItem[]>(`/topics/${topicId}/tests`)
  return data
}
