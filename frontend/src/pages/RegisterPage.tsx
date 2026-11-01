import { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { useAppDispatch } from '../hooks'
import { setCredentials } from '../features/auth/authSlice'
import api from '../api/axiosInstance'
import type { AuthResponse } from '../api/profile'
import AuthShell from '../components/AuthShell'
import { Button } from '../components/ui/Button'
import { inputClass, labelClass } from '../components/ui/field'

export default function RegisterPage() {
  const navigate = useNavigate()
  const dispatch = useAppDispatch()
  const [displayName, setDisplayName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [errorMsg, setErrorMsg] = useState('')
  const [submitting, setSubmitting] = useState(false)

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setErrorMsg('')
    setSubmitting(true)
    try {
      await api.post('/auth/register', { email, password, displayName })
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { message?: string } } })?.response?.data?.message ?? 'Registration failed.'
      setErrorMsg(msg)
      setSubmitting(false)
      return
    }
    // Sign the new account straight in so the onboarding questionnaire comes next
    try {
      const { data } = await api.post<AuthResponse>('/auth/login', { email, password })
      dispatch(setCredentials({ user: data.user, accessToken: data.accessToken }))
      navigate('/onboarding')
    } catch {
      navigate('/login')
    }
  }

  return (
    <AuthShell
      title="Create your PrepPilot account"
      subtitle="Free, with no daily limits."
      footer={
        <p>
          Already have an account?{' '}
          <Link to="/login" className="font-medium text-ink underline decoration-edge underline-offset-4 hover:decoration-ink">
            Sign in
          </Link>
        </p>
      }
    >
      <form onSubmit={handleSubmit} className="flex flex-col gap-4">
        <label className={labelClass}>
          Display name
          <input
            type="text"
            autoComplete="name"
            value={displayName}
            onChange={(e) => setDisplayName(e.target.value)}
            required
            className={inputClass}
          />
        </label>
        <label className={labelClass}>
          Email
          <input
            type="email"
            autoComplete="email"
            placeholder="you@example.com"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            className={inputClass}
          />
        </label>
        <label className={labelClass}>
          Password
          <input
            type="password"
            autoComplete="new-password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            minLength={8}
            aria-describedby="password-rule"
            className={inputClass}
          />
          <span id="password-rule" className="type-meta font-normal">
            At least 8 characters.
          </span>
        </label>

        {errorMsg && (
          <p role="alert" className="text-sm text-redpen">
            {errorMsg}
          </p>
        )}

        <Button type="submit" variant="primary" size="lg" disabled={submitting} className="mt-1 w-full">
          {submitting ? 'Creating your account…' : 'Register'}
        </Button>
      </form>
    </AuthShell>
  )
}
