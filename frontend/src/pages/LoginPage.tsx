import { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { useAppDispatch } from '../hooks'
import { setCredentials, setLoading, setError } from '../features/auth/authSlice'
import api from '../api/axiosInstance'

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
    <div className="page-shell">
      <div className="card auth-card">
        <h1>Sign in to PrepPilot</h1>
        <form onSubmit={handleSubmit}>
          <label>
            Email
            <input
              type="email"
              placeholder="Email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
            />
          </label>
          <label>
            Password
            <input
              type="password"
              placeholder="Password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
          </label>
          {errorMsg && <p>{errorMsg}</p>}
          <button type="submit" className="primary-button">
            Sign In
          </button>
        </form>
        <a className="secondary-button" href="/api/v1/auth/google">
          Sign in with Google
        </a>
        <p className="muted-text">
          No account? <Link to="/register">Register</Link>
        </p>
      </div>
    </div>
  )
}
