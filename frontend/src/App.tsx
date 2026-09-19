import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { useAppSelector } from './hooks'
import { useSilentRefresh } from './features/auth/useSilentRefresh'
import LoginPage from './pages/LoginPage'
import RegisterPage from './pages/RegisterPage'
import DashboardPage from './pages/DashboardPage'
import OAuthCallbackPage from './pages/OAuthCallbackPage'
import LearnModePage from './pages/LearnModePage'
import TestPage from './pages/TestPage'
import TestReportPage from './pages/TestReportPage'
import TestHistoryPage from './pages/TestHistoryPage'
import MockInterviewPage from './pages/MockInterviewPage'
import MockInterviewHistoryPage from './pages/MockInterviewHistoryPage'
import MockInterviewReportPage from './pages/MockInterviewReportPage'

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
        <Route
          path="/topics/:topicId/learn"
          element={
            <ProtectedRoute>
              <LearnModePage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/topics/:topicId/test"
          element={
            <ProtectedRoute>
              <TestPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/topics/:topicId/tests"
          element={
            <ProtectedRoute>
              <TestHistoryPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/topics/:topicId/tests/:testId/report"
          element={
            <ProtectedRoute>
              <TestReportPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/topics/:topicId/interviews"
          element={
            <ProtectedRoute>
              <MockInterviewPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/topics/:topicId/interviews/history"
          element={
            <ProtectedRoute>
              <MockInterviewHistoryPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/topics/:topicId/interviews/:sessionId/report"
          element={
            <ProtectedRoute>
              <MockInterviewReportPage />
            </ProtectedRoute>
          }
        />
        <Route path="*" element={<Navigate to="/dashboard" replace />} />
      </Routes>
    </BrowserRouter>
  )
}
