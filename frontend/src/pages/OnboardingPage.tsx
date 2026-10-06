import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { GraduationCap } from 'lucide-react'
import { useAppDispatch, useAppSelector } from '../hooks'
import { clearCredentials, setCredentials } from '../features/auth/authSlice'
import api from '../api/axiosInstance'
import { DOMAIN_OPTIONS, EXPERIENCE_OPTIONS, updateProfile } from '../api/profile'
import type { ProfileExperience } from '../api/profile'
import AuthShell from '../components/AuthShell'

const OTHER_DOMAIN = 'Other'

/**
 * The questionnaire every new user answers before reaching the dashboard (Google sign-ups
 * included). Already-onboarded users come back here from the dashboard to edit their answers.
 */
export default function OnboardingPage() {
  const dispatch = useAppDispatch()
  const navigate = useNavigate()
  const user = useAppSelector((state) => state.auth.user)
  const editing = user?.onboardingCompleted ?? false

  const savedDomain = user?.preferredDomain ?? ''
  const savedDomainIsListed = DOMAIN_OPTIONS.includes(savedDomain)
  const [domainChoice, setDomainChoice] = useState(
    savedDomain ? (savedDomainIsListed ? savedDomain : OTHER_DOMAIN) : ''
  )
  const [otherDomain, setOtherDomain] = useState(savedDomain && !savedDomainIsListed ? savedDomain : '')
  const [experience, setExperience] = useState<ProfileExperience | null>(user?.experienceLevel ?? null)
  const [errorMsg, setErrorMsg] = useState('')
  const [saving, setSaving] = useState(false)

  const preferredDomain = (domainChoice === OTHER_DOMAIN ? otherDomain : domainChoice).trim()
  const canSubmit = preferredDomain.length > 0 && experience !== null && !saving

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!experience || !preferredDomain) return
    setErrorMsg('')
    setSaving(true)
    try {
      const data = await updateProfile({ preferredDomain, experienceLevel: experience })
      dispatch(setCredentials({ user: data.user, accessToken: data.accessToken }))
      navigate('/dashboard', { replace: true })
    } catch {
      setErrorMsg('Could not save your answers. Please try again.')
      setSaving(false)
    }
  }

  async function handleLogout() {
    await api.post('/auth/logout').catch(() => null)
    dispatch(clearCredentials())
    navigate('/login')
  }

  const chipClass = (selected: boolean) =>
    `rounded-full border px-3 py-1.5 text-sm font-semibold transition-colors ${
      selected ? 'border-primary bg-primary-subtle text-primary' : 'border-border bg-surface text-fg hover:bg-surface-hover'
    }`

  return (
    <AuthShell
      title={editing ? 'Update your profile' : 'Tell us about yourself'}
      subtitle="Two quick questions so PrepPilot can pitch content at the right level."
      footer={
        editing ? (
          <Link to="/dashboard" className="font-semibold text-primary">
            Back to dashboard
          </Link>
        ) : (
          <p>
            Signed in as {user?.email}.{' '}
            <button type="button" onClick={handleLogout} className="font-semibold text-primary">
              Sign out
            </button>
          </p>
        )
      }
    >
      <form onSubmit={handleSubmit} className="flex flex-col gap-7">
        <fieldset className="flex flex-col gap-3">
          <legend className="mb-3 text-sm font-bold text-fg">What is your preferred domain?</legend>
          <div className="flex flex-wrap gap-2">
            {[...DOMAIN_OPTIONS, OTHER_DOMAIN].map((domain) => (
              <button
                key={domain}
                type="button"
                aria-pressed={domainChoice === domain}
                onClick={() => setDomainChoice(domain)}
                className={chipClass(domainChoice === domain)}
              >
                {domain}
              </button>
            ))}
          </div>
          {domainChoice === OTHER_DOMAIN && (
            <input
              type="text"
              placeholder="e.g. Game development"
              value={otherDomain}
              onChange={(e) => setOtherDomain(e.target.value)}
              maxLength={100}
              autoFocus
              aria-label="Your domain"
              className="w-full rounded-lg border border-border bg-surface px-3.5 py-2.5 text-sm text-fg outline-none transition-colors placeholder:text-muted focus:border-primary focus:ring-2 focus:ring-primary/20"
            />
          )}
        </fieldset>

        <fieldset className="flex flex-col gap-3">
          <legend className="mb-3 text-sm font-bold text-fg">What is your current experience?</legend>
          <div className="grid grid-cols-2 gap-2">
            {EXPERIENCE_OPTIONS.map((option) => {
              const selected = experience === option.value
              return (
                <button
                  key={option.value}
                  type="button"
                  aria-pressed={selected}
                  onClick={() => setExperience(option.value)}
                  className={`rounded-xl border p-3 text-left transition-colors ${
                    selected ? 'border-primary bg-primary-subtle' : 'border-border bg-surface hover:bg-surface-hover'
                  }`}
                >
                  <span className="block text-sm font-bold text-fg">{option.label}</span>
                  <span className="mt-0.5 block text-xs text-muted">{option.hint}</span>
                </button>
              )
            })}
          </div>
          {experience === 'STUDENT' && (
            <p className="flex items-start gap-2 rounded-lg bg-primary-subtle px-3 py-2.5 text-xs text-fg">
              <GraduationCap size={15} className="mt-px shrink-0 text-primary" />
              Learn and Test Mode will focus on what campus placements ask, and mock interviews will be pitched
              at student level.
            </p>
          )}
        </fieldset>

        {errorMsg && <p className="text-sm font-medium text-danger">{errorMsg}</p>}

        <button
          type="submit"
          disabled={!canSubmit}
          className="flex h-11 w-full items-center justify-center rounded-lg bg-primary text-sm font-bold text-primary-fg transition-colors hover:bg-primary-hover disabled:cursor-not-allowed disabled:opacity-60"
        >
          {saving ? 'Saving…' : editing ? 'Save changes' : 'Continue'}
        </button>
      </form>
    </AuthShell>
  )
}
