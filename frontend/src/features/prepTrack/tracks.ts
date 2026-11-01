import type { ProfileExperience } from '../../api/profile'

/**
 * How the experience answer from onboarding shapes each mode. College students get the placement
 * track; every other answer (or none) gets the professional track. Keep this in step with the
 * STUDENT instructions in ai-service/app/prompts.py and MockInterviewService.
 */
export type TrackKey = 'placement' | 'professional'

export interface Track {
  label: string
  /** Who the track is for, shown under the toggle. */
  audience: string
  modes: Array<{ title: string; body: string }>
}

export const TRACKS: Record<TrackKey, Track> = {
  placement: {
    label: 'Placement',
    audience: 'For college students preparing for campus placements',
    modes: [
      {
        title: 'Learn',
        body: 'Fundamentals first, with the questions placement drives ask and the mistakes students commonly make.',
      },
      {
        title: 'Test',
        body: 'Easy and intermediate questions, graded against what a student is expected to know.',
      },
      {
        title: 'Mock interview',
        body: 'A student-level interview with mostly easy questions. You only pick how long it runs.',
      },
    ],
  },
  professional: {
    label: 'Professional',
    audience: 'For anyone with work experience, from 0–3 years to 13+',
    modes: [
      {
        title: 'Learn',
        body: 'The tutor asks how deep to go, from quick revision notes to real-world trade-offs.',
      },
      {
        title: 'Test',
        body: 'Beginner to advanced questions across concepts, scenarios and code.',
      },
      {
        title: 'Mock interview',
        body: 'Pick your level, from Junior to Advanced, and a difficulty. The bar for a strong answer matches it.',
      },
    ],
  },
}

export function trackFor(experience: ProfileExperience | null | undefined): TrackKey {
  return experience === 'STUDENT' ? 'placement' : 'professional'
}
