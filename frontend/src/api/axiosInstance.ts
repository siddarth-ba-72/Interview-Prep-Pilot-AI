import axios from 'axios'
import { store } from '../store'
import { setCredentials, clearCredentials } from '../features/auth/authSlice'
import { getApiBaseUrl } from './config'
import { refreshSession } from './refreshSession'
import { trackLimitError } from '../features/analytics/clarity'

const api = axios.create({
  baseURL: getApiBaseUrl(),
  withCredentials: true, // send refresh token cookie automatically
})

// Attach JWT to every request
api.interceptors.request.use((config) => {
  const token = store.getState().auth.accessToken
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// Silent refresh on 401
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const original = error.config

    const isRefreshCall = original.url?.includes('/auth/refresh')

    if (error.response?.status === 401 && !original._retry && !isRefreshCall) {
      original._retry = true

      try {
        const data = await refreshSession()
        store.dispatch(setCredentials({ user: data.user, accessToken: data.accessToken }))
        original.headers.Authorization = `Bearer ${data.accessToken}`
        return api(original)
      } catch {
        store.dispatch(clearCredentials())
        if (window.location.pathname !== '/login') {
          window.location.href = '/login'
        }
        return Promise.reject(error)
      }
    }

    trackLimitError(error.response?.data?.error?.code)
    return Promise.reject(error)
  }
)

export default api
