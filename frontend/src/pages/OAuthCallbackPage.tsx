import { useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAppDispatch } from '../hooks'
import { setCredentials } from '../features/auth/authSlice'
import api from '../api/axiosInstance'

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
    <div className="page-shell">
      <div className="card auth-card">
        <p>Signing you in...</p>
      </div>
    </div>
  )
}
