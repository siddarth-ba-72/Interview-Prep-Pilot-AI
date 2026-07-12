import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { useAppSelector } from './hooks'
import { useSilentRefresh } from './features/auth/useSilentRefresh'
import LoginPage from './pages/LoginPage'
import RegisterPage from './pages/RegisterPage'
import DashboardPage from './pages/DashboardPage'
import OAuthCallbackPage from './pages/OAuthCallbackPage'

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { accessToken, status } = useAppSelector((state) => state.auth)
  if (status === 'loading') return null
  return accessToken ? <>{children}</> : <Navigate to="/login" replace />
}

export default function App() {
  useSilentRefresh()

  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/register" element={<RegisterPage />} />
        <Route path="/auth/callback" element={<OAuthCallbackPage />} />
        <Route
          path="/dashboard"
          element={
            <ProtectedRoute>
              <DashboardPage />
            </ProtectedRoute>
          }
        />
        <Route path="*" element={<Navigate to="/dashboard" replace />} />
      </Routes>
    </BrowserRouter>
  )
}
