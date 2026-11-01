import { useState } from 'react'
import { useNavigate, Link, useSearchParams } from 'react-router-dom'
import { useAppDispatch } from '../hooks'
import { setCredentials, setLoading, setError } from '../features/auth/authSlice'
import api from '../api/axiosInstance'
import { getBackendUrl } from '../api/config'
import AuthShell from '../components/AuthShell'
import { Button, buttonClass } from '../components/ui/Button'
import { inputClass, labelClass } from '../components/ui/field'

export default function LoginPage() {
  const dispatch = useAppDispatch()
  const navigate = useNavigate()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [searchParams] = useSearchParams()
  const oauthError = searchParams.get('oauth_error')
  const [errorMsg, setErrorMsg] = useState(oauthError ? `Google sign-in failed (${oauthError}). Please try again.` : '')

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setErrorMsg('')
    setSubmitting(true)
    dispatch(setLoading())
    try {
      const { data } = await api.post('/auth/login', { email, password })
      dispatch(setCredentials({ user: data.user, accessToken: data.accessToken }))
      navigate('/dashboard')
    } catch {
      dispatch(setError())
      setErrorMsg('Invalid email or password.')
      setSubmitting(false)
    }
  }

  return (
    <AuthShell
      title="Sign in to PrepPilot"
      subtitle="Pick up where you left off."
      footer={
        <p>
          No account?{' '}
          <Link to="/register" className="font-medium text-ink underline decoration-edge underline-offset-4 hover:decoration-ink">
            Register
          </Link>
        </p>
      }
    >
      <form onSubmit={handleSubmit} className="flex flex-col gap-4">
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
            autoComplete="current-password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            className={inputClass}
          />
        </label>

        {errorMsg && (
          <p role="alert" className="text-sm text-redpen">
            {errorMsg}
          </p>
        )}

        <Button type="submit" variant="primary" size="lg" disabled={submitting} className="mt-1 w-full">
          {submitting ? 'Signing in…' : 'Sign in'}
        </Button>
      </form>

      <div className="my-5 flex items-center gap-3 text-[13px] text-pencil">
        <span className="h-px flex-1 bg-line" />
        or
        <span className="h-px flex-1 bg-line" />
      </div>

      <a href={getBackendUrl('/oauth2/authorization/google')} className={buttonClass({ size: 'lg', className: 'w-full' })}>
        <GoogleMark />
        Sign in with Google
      </a>
    </AuthShell>
  )
}

/** Google's "G", as its sign-in guidelines ask for on the button. */
function GoogleMark() {
  return (
    <svg width="16" height="16" viewBox="0 0 48 48" aria-hidden>
      <path fill="#EA4335" d="M24 9.5c3.54 0 6.71 1.22 9.21 3.6l6.85-6.85C35.9 2.38 30.47 0 24 0 14.62 0 6.51 5.38 2.56 13.22l7.98 6.19C12.43 13.72 17.74 9.5 24 9.5z" />
      <path fill="#4285F4" d="M46.98 24.55c0-1.57-.15-3.09-.38-4.55H24v9.02h12.94c-.58 2.96-2.26 5.48-4.78 7.18l7.73 6c4.51-4.18 7.09-10.36 7.09-17.65z" />
      <path fill="#FBBC05" d="M10.53 28.59c-.48-1.45-.76-2.99-.76-4.59s.27-3.14.76-4.59l-7.98-6.19C.92 16.46 0 20.12 0 24c0 3.88.92 7.54 2.56 10.78l7.97-6.19z" />
      <path fill="#34A853" d="M24 48c6.48 0 11.93-2.13 15.89-5.81l-7.73-6c-2.15 1.45-4.92 2.3-8.16 2.3-6.26 0-11.57-4.22-13.47-9.91l-7.98 6.19C6.51 42.62 14.62 48 24 48z" />
    </svg>
  )
}
