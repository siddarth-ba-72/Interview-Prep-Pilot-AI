import { useAppSelector, useAppDispatch } from '../hooks'
import { clearCredentials } from '../features/auth/authSlice'
import api from '../api/axiosInstance'
import { useNavigate } from 'react-router-dom'

export default function DashboardPage() {
  const user = useAppSelector((state) => state.auth.user)
  const dispatch = useAppDispatch()
  const navigate = useNavigate()

  async function handleLogout() {
    await api.post('/auth/logout').catch(() => null)
    dispatch(clearCredentials())
    navigate('/login')
  }

  return (
    <div className="page-shell">
      <div className="card dashboard-card">
        <h1>Welcome, {user?.displayName}!</h1>
        <p className="muted-text">{user?.email}</p>
        <button onClick={handleLogout} className="primary-button">
          Logout
        </button>
      </div>
    </div>
  )
}
