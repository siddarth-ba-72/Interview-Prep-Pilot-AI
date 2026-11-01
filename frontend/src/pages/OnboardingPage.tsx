import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAppDispatch, useAppSelector } from '../hooks'
import { clearCredentials, setCredentials } from '../features/auth/authSlice'
import api from '../api/axiosInstance'
import { DOMAIN_OPTIONS, EXPERIENCE_OPTIONS, updateProfile } from '../api/profile'
import type { ProfileExperience } from '../api/profile'
import AuthShell from '../components/AuthShell'
import { Button } from '../components/ui/Button'
import { inputClass } from '../components/ui/field'
import Notice from '../components/ui/Notice'

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

  const optionClass = (selected: boolean) =>
    `rounded-md border text-left transition-[border-color,background-color,transform] duration-150 active:scale-[0.98] ${
      selected ? 'border-ink bg-sheet ring-1 ring-ink' : 'border-line bg-sheet hover:border-edge hover:bg-wash'
    }`

  return (
    <AuthShell
      title={editing ? 'Update your profile' : 'Tell us about yourself'}
      subtitle="Two questions, so Learn, Test and Mock interview are pitched at the right level."
      footer={
        editing ? (
          <Link to="/dashboard" className="font-medium text-ink underline decoration-edge underline-offset-4 hover:decoration-ink">
            Back to your topics
          </Link>
        ) : (
          <p>
            Signed in as <span data-clarity-mask="True">{user?.email}</span>.{' '}
            <button type="button" onClick={handleLogout} className="font-medium text-ink underline decoration-edge underline-offset-4 hover:decoration-ink">
              Sign out
            </button>
          </p>
        )
      }
    >
      <form onSubmit={handleSubmit} className="flex flex-col gap-8">
        <fieldset>
          <legend className="mb-3 text-sm font-medium text-ink">What is your preferred domain?</legend>
          <div className="flex flex-wrap gap-2">
            {[...DOMAIN_OPTIONS, OTHER_DOMAIN].map((domain) => (
              <button
                key={domain}
                type="button"
                aria-pressed={domainChoice === domain}
                onClick={() => setDomainChoice(domain)}
                className={`${optionClass(domainChoice === domain)} h-9 px-3 text-sm text-ink`}
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
              className={`${inputClass} mt-3`}
            />
          )}
        </fieldset>

        <fieldset>
          <legend className="mb-3 text-sm font-medium text-ink">What is your current experience?</legend>
          <div className="grid grid-cols-2 gap-2">
            {EXPERIENCE_OPTIONS.map((option) => {
              const selected = experience === option.value
              return (
                <button
                  key={option.value}
                  type="button"
                  aria-pressed={selected}
                  onClick={() => setExperience(option.value)}
                  className={`${optionClass(selected)} px-3 py-2.5`}
                >
                  <span className="block text-sm font-medium text-ink">{option.label}</span>
                  <span className="type-meta block">{option.hint}</span>
                </button>
              )
            })}
          </div>
          {experience === 'STUDENT' && (
            <Notice tone="info" className="mt-3">
              Learn and Test will focus on what campus placements ask, and mock interviews will be pitched at student level.
            </Notice>
          )}
        </fieldset>

        {errorMsg && <Notice>{errorMsg}</Notice>}

        <Button type="submit" variant="primary" size="lg" disabled={!canSubmit} className="w-full">
          {saving ? 'Saving…' : editing ? 'Save changes' : 'Continue'}
        </Button>
      </form>
    </AuthShell>
  )
}
