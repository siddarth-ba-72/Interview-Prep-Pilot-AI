import api from './axiosInstance'

/** The onboarding answer to "current experience". STUDENT tailors Learn, Test and Mock Interview. */
export type ProfileExperience = 'STUDENT' | 'YEARS_0_3' | 'YEARS_3_5' | 'YEARS_5_8' | 'YEARS_8_13' | 'YEARS_13_PLUS'

/** ADMIN opens the read-only admin dashboard; it is granted by hand in the database. */
export type Role = 'USER' | 'ADMIN'

export interface User {
  id: string
  email: string
  displayName: string
  preferredDomain: string | null
  experienceLevel: ProfileExperience | null
  onboardingCompleted: boolean
  role: Role
}

export interface AuthResponse {
  user: User
  accessToken: string
}

export const EXPERIENCE_OPTIONS: Array<{ value: ProfileExperience; label: string; hint: string }> = [
  { value: 'STUDENT', label: 'College student', hint: 'Preparing for campus placements' },
  { value: 'YEARS_0_3', label: '0-3 years', hint: 'Early career' },
  { value: 'YEARS_3_5', label: '3-5 years', hint: 'Mid level' },
  { value: 'YEARS_5_8', label: '5-8 years', hint: 'Senior' },
  { value: 'YEARS_8_13', label: '8-13 years', hint: 'Staff / lead' },
  { value: 'YEARS_13_PLUS', label: '13+ years', hint: 'Principal / architect' },
]

export const DOMAIN_OPTIONS = [
  'Frontend',
  'Backend',
  'Full stack',
  'Mobile',
  'Data science / ML',
  'Data engineering',
  'DevOps / Cloud',
  'QA / Testing',
  'Embedded / Systems',
  'Security',
]

/** Saves the questionnaire. The response carries a new access token, since the experience
 * level is a token claim that the backend reads on every Learn / Test / Interview request. */
export async function updateProfile(profile: {
  preferredDomain: string
  experienceLevel: ProfileExperience
}): Promise<AuthResponse> {
  const { data } = await api.put<AuthResponse>('/users/me/profile', profile)
  return data
}
