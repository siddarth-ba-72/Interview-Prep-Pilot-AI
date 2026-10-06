import { useEffect } from 'react'
import { BrowserRouter, Routes, Route, Navigate, useLocation } from 'react-router-dom'
import { useAppSelector } from './hooks'
import { useSilentRefresh } from './features/auth/useSilentRefresh'
import LoginPage from './pages/LoginPage'
import RegisterPage from './pages/RegisterPage'
import DashboardPage from './pages/DashboardPage'
import OAuthCallbackPage from './pages/OAuthCallbackPage'
import OnboardingPage from './pages/OnboardingPage'
import HowItWorksPage from './pages/HowItWorksPage'
import LearnModePage from './pages/LearnModePage'
import TestPage from './pages/TestPage'
import TestReportPage from './pages/TestReportPage'
import TestHistoryPage from './pages/TestHistoryPage'
import MockInterviewPage from './pages/MockInterviewPage'
import MockInterviewHistoryPage from './pages/MockInterviewHistoryPage'
import MockInterviewReportPage from './pages/MockInterviewReportPage'

function ScrollToTop() {
  const { pathname } = useLocation()
  useEffect(() => {
    window.scrollTo(0, 0)
  }, [pathname])
  return null
}

function ProtectedRoute({
  children,
  skipOnboardingCheck = false,
}: {
  children: React.ReactNode
  skipOnboardingCheck?: boolean
}) {
  const { accessToken, status, user } = useAppSelector((state) => state.auth)
  if (status === 'loading') return null
  if (!accessToken) return <Navigate to="/login" replace />
  // Users who have not answered the questionnaire yet (new sign-ups) answer it before anything else
  if (!skipOnboardingCheck && user && !user.onboardingCompleted) return <Navigate to="/onboarding" replace />
  return <>{children}</>
}

export default function App() {
  useSilentRefresh()

  return (
    <BrowserRouter>
      <ScrollToTop />
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/register" element={<RegisterPage />} />
        <Route path="/auth/callback" element={<OAuthCallbackPage />} />
        <Route path="/how-it-works" element={<HowItWorksPage />} />
        <Route
          path="/onboarding"
          element={
            <ProtectedRoute skipOnboardingCheck>
              <OnboardingPage />
            </ProtectedRoute>
          }
        />
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
