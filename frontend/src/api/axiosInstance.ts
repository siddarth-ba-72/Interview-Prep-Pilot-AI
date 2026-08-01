import axios from 'axios'
import { store } from '../store'
import { setCredentials, clearCredentials } from '../features/auth/authSlice'
import { getApiBaseUrl } from './config'

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
let isRefreshing = false

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const original = error.config

    const isRefreshCall = original.url?.includes('/auth/refresh')

    if (error.response?.status === 401 && !original._retry && !isRefreshing && !isRefreshCall) {
      original._retry = true
      isRefreshing = true

      try {
        const { data } = await axios.post(`${getApiBaseUrl()}/auth/refresh`, {}, { withCredentials: true })
        store.dispatch(setCredentials({ user: data.user, accessToken: data.accessToken }))
        original.headers.Authorization = `Bearer ${data.accessToken}`
        return api(original)
      } catch {
        store.dispatch(clearCredentials())
        if (window.location.pathname !== '/login') {
          window.location.href = '/login'
        }
        return Promise.reject(error)
      } finally {
        isRefreshing = false
      }
    }

    return Promise.reject(error)
  }
)

export default api
