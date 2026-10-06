import axios from 'axios'
import { getApiBaseUrl } from './config'
import type { AuthResponse } from './profile'

let inFlight: Promise<AuthResponse> | null = null

/**
 * Exchange the HttpOnly refresh token cookie for a new access token.
 * Concurrent callers share one request: the server rotates the refresh token,
 * so parallel requests carrying the same cookie would race each other.
 */
export function refreshSession(): Promise<AuthResponse> {
  if (!inFlight) {
    inFlight = axios
      .post<AuthResponse>(`${getApiBaseUrl()}/auth/refresh`, {}, { withCredentials: true })
      .then(({ data }) => data)
      .finally(() => {
        inFlight = null
      })
  }
  return inFlight
}
