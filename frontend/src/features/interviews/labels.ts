import type { Difficulty, ExperienceLevel, InterviewConfig } from '../../api/interviews'

/** A report is scored out of 100 and passes at 75 (MockInterviewService). */
export const INTERVIEW_MAX = 100
export const INTERVIEW_PASS = 75

export const EXPERIENCE_LEVELS: Array<{ value: ExperienceLevel; label: string; years: string }> = [
  { value: 'STUDENT', label: 'Student', years: 'Still in college' },
  { value: 'JUNIOR', label: 'Junior', years: '0–2 years' },
  { value: 'INTERMEDIATE', label: 'Intermediate', years: '2–5 years' },
  { value: 'SENIOR', label: 'Senior', years: '5–8 years' },
  { value: 'MASTER', label: 'Master', years: '8–13 years' },
  { value: 'ADVANCED', label: 'Advanced', years: '13+ years' },
]

export const DIFFICULTIES: Array<{ value: Difficulty; label: string; hint: string }> = [
  { value: 'EASY', label: 'Easy', hint: 'Warm-up pace' },
  { value: 'MEDIUM', label: 'Medium', hint: 'A realistic bar' },
  { value: 'HARD', label: 'Hard', hint: 'Pushes back hard' },
]

export const DURATIONS = [30, 45, 60]

export function levelLabel(level: ExperienceLevel): string {
  return EXPERIENCE_LEVELS.find((option) => option.value === level)?.label ?? level
}

export function difficultyLabel(difficulty: Difficulty): string {
  return DIFFICULTIES.find((option) => option.value === difficulty)?.label ?? difficulty
}

/** "Intermediate · Medium · 30 min" */
export function configLabel(config: InterviewConfig | null): string {
  if (!config) return 'Setup unavailable'
  return `${levelLabel(config.experienceLevel)} · ${difficultyLabel(config.difficulty)} · ${config.durationMinutes} min`
}
