import { useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAppDispatch } from '../hooks'
import { setCredentials } from '../features/auth/authSlice'
import api from '../api/axiosInstance'
import AuthShell from '../components/AuthShell'

/**
 * After Google OAuth, the backend redirects here with the access token
 * in the URL fragment: /auth/callback#token=<jwt>
 *
 * We read it once, store in Redux (memory only), strip it from the URL,
 * then fetch the user profile.
 */
export default function OAuthCallbackPage() {
  const dispatch = useAppDispatch()
  const navigate = useNavigate()

  useEffect(() => {
    const hash = window.location.hash
    const params = new URLSearchParams(hash.replace('#', '?'))
    const token = params.get('token')

    if (!token) {
      navigate('/login')
      return
    }

    // Strip token from URL immediately
    window.history.replaceState(null, '', '/auth/callback')

    api
      .get('/users/me', { headers: { Authorization: `Bearer ${token}` } })
      .then(({ data }) => {
        dispatch(setCredentials({ user: data, accessToken: token }))
        navigate('/dashboard')
      })
      .catch(() => navigate('/login'))
  }, [dispatch, navigate])

  return (
    <AuthShell title="Signing you in...">
      <div className="flex items-center gap-3 text-sm text-muted">
        <span className="h-4 w-4 animate-spin rounded-full border-2 border-border border-t-primary" />
        Verifying your Google account
      </div>
    </AuthShell>
  )
}
