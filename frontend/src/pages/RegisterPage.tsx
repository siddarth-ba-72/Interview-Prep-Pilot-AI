import { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import api from '../api/axiosInstance'
import AuthShell from '../components/AuthShell'

export default function RegisterPage() {
  const navigate = useNavigate()
  const [displayName, setDisplayName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [errorMsg, setErrorMsg] = useState('')

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setErrorMsg('')
    try {
      await api.post('/auth/register', { email, password, displayName })
      navigate('/login')
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { message?: string } } })?.response?.data?.message ??
        'Registration failed.'
      setErrorMsg(msg)
    }
  }

  return (
    <AuthShell
      title="Create your PrepPilot account"
      subtitle="Start prepping for your next interview today."
      footer={
        <p>
          Already have an account?{' '}
          <Link to="/login" className="font-semibold text-primary">
            Sign in
          </Link>
        </p>
      }
    >
      <form onSubmit={handleSubmit} className="flex flex-col gap-4">
        <label className="flex flex-col gap-1.5 text-sm font-semibold text-fg">
          Display name
          <input
            type="text"
            placeholder="Jane Doe"
            value={displayName}
            onChange={(e) => setDisplayName(e.target.value)}
            required
            className="w-full rounded-lg border border-border bg-surface px-3.5 py-2.5 text-sm font-normal text-fg outline-none transition-colors placeholder:text-muted focus:border-primary focus:ring-2 focus:ring-primary/20"
          />
        </label>
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
            placeholder="Min 8 characters"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            minLength={8}
            className="w-full rounded-lg border border-border bg-surface px-3.5 py-2.5 text-sm font-normal text-fg outline-none transition-colors placeholder:text-muted focus:border-primary focus:ring-2 focus:ring-primary/20"
          />
        </label>

        {errorMsg && <p className="text-sm font-medium text-danger">{errorMsg}</p>}

        <button
          type="submit"
          className="mt-1 flex h-11 w-full items-center justify-center rounded-lg bg-primary text-sm font-bold text-primary-fg transition-colors hover:bg-primary-hover"
        >
          Register
        </button>
      </form>
    </AuthShell>
  )
}
