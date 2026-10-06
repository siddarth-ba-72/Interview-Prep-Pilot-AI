import axios from 'axios'
import { getApiBaseUrl } from './config'

export interface RefreshResponse {
  user: { id: string; email: string; displayName: string }
  accessToken: string
}

let inFlight: Promise<RefreshResponse> | null = null

/**
 * Exchange the HttpOnly refresh token cookie for a new access token.
 * Concurrent callers share one request: the server rotates the refresh token,
 * so parallel requests carrying the same cookie would race each other.
 */
export function refreshSession(): Promise<RefreshResponse> {
  if (!inFlight) {
    inFlight = axios
      .post<RefreshResponse>(`${getApiBaseUrl()}/auth/refresh`, {}, { withCredentials: true })
      .then(({ data }) => data)
      .finally(() => {
        inFlight = null
      })
  }
  return inFlight
}
