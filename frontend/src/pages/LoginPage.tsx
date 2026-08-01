import { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { useAppDispatch } from '../hooks'
import { setCredentials, setLoading, setError } from '../features/auth/authSlice'
import api from '../api/axiosInstance'
import AuthShell from '../components/AuthShell'

export default function LoginPage() {
  const dispatch = useAppDispatch()
  const navigate = useNavigate()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [errorMsg, setErrorMsg] = useState('')

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setErrorMsg('')
    dispatch(setLoading())
    try {
      const { data } = await api.post('/auth/login', { email, password })
      dispatch(setCredentials({ user: data.user, accessToken: data.accessToken }))
      navigate('/dashboard')
    } catch {
      dispatch(setError())
      setErrorMsg('Invalid email or password.')
    }
  }

  return (
    <AuthShell
      title="Sign in to PrepPilot"
      subtitle="Pick up where you left off."
      footer={
        <p>
          No account?{' '}
          <Link to="/register" className="font-semibold text-primary">
            Register
          </Link>
        </p>
      }
    >
      <form onSubmit={handleSubmit} className="flex flex-col gap-4">
        <label className="flex flex-col gap-1.5 text-sm font-semibold text-fg">
          Email
          <input
            type="email"
            placeholder="you@example.com"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            className="w-full rounded-lg border border-border bg-surface px-3.5 py-2.5 text-sm font-normal text-fg outline-none transition-colors placeholder:text-muted focus:border-primary focus:ring-2 focus:ring-primary/20"
          />
        </label>
        <label className="flex flex-col gap-1.5 text-sm font-semibold text-fg">
          Password
          <input
            type="password"
            placeholder="••••••••"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            className="w-full rounded-lg border border-border bg-surface px-3.5 py-2.5 text-sm font-normal text-fg outline-none transition-colors placeholder:text-muted focus:border-primary focus:ring-2 focus:ring-primary/20"
          />
        </label>

        {errorMsg && <p className="text-sm font-medium text-danger">{errorMsg}</p>}

        <button
          type="submit"
          className="mt-1 flex h-11 w-full items-center justify-center rounded-lg bg-primary text-sm font-bold text-primary-fg transition-colors hover:bg-primary-hover"
        >
          Sign In
        </button>
      </form>

      <div className="my-5 flex items-center gap-3 text-xs font-medium uppercase tracking-wide text-muted">
        <span className="h-px flex-1 bg-border" />
        or
        <span className="h-px flex-1 bg-border" />
      </div>

      <a
        href="/oauth2/authorization/google"
        className="flex h-11 w-full items-center justify-center rounded-lg border border-border bg-surface text-sm font-bold text-fg transition-colors hover:bg-surface-hover hover:no-underline"
      >
        Sign in with Google
      </a>
    </AuthShell>
  )
}
