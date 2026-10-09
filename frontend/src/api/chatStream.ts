import { fetchEventSource } from '@microsoft/fetch-event-source'
import { store } from '../store'
import { setCredentials, clearCredentials } from '../features/auth/authSlice'
import { getApiBaseUrl } from './config'
import { refreshSession } from './refreshSession'
import { withRetryTime } from './usage'
import { trackLimitError } from '../features/analytics/clarity'

export type StreamEvent = { type: 'token'; token: string } | { type: 'error'; message: string } | { type: 'done' }

interface StreamHandlers {
  onEvent: (event: StreamEvent) => void
  onFatalError: (message: string) => void
}

class NeedsRefresh extends Error {}

async function refreshAccessToken(): Promise<string | null> {
  try {
    const data = await refreshSession()
    store.dispatch(setCredentials({ user: data.user, accessToken: data.accessToken }))
    return data.accessToken
  } catch {
    store.dispatch(clearCredentials())
    return null
  }
}

export async function streamChatMessage(topicId: string, content: string, handlers: StreamHandlers): Promise<void> {
  let token = store.getState().auth.accessToken

  async function attempt(alreadyRetried: boolean): Promise<void> {
    try {
      await fetchEventSource(`${getApiBaseUrl()}/topics/${topicId}/chat/messages`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: token ? `Bearer ${token}` : '',
        },
        credentials: 'include',
        body: JSON.stringify({ content }),
        openWhenHidden: true,
        async onopen(response) {
          const contentType = response.headers.get('content-type') ?? ''
          if (response.ok && contentType.includes('text/event-stream')) {
            return
          }
          if (response.status === 401 && !alreadyRetried) {
            throw new NeedsRefresh()
          }
          throw new Error(`Unexpected response: ${response.status}`)
        },
        onmessage(ev) {
          if (ev.data === '[DONE]') {
            handlers.onEvent({ type: 'done' })
            return
          }
          try {
            const parsed = JSON.parse(ev.data)
            if (parsed.error) {
              trackLimitError(parsed.code)
              handlers.onEvent({ type: 'error', message: withRetryTime(parsed.error, parsed.retryAt) })
            } else if (parsed.token) {
              handlers.onEvent({ type: 'token', token: parsed.token })
            }
          } catch {
            // ignore malformed SSE frame
          }
        },
        onerror(err) {
          throw err
        },
      })
    } catch (err) {
      if (err instanceof NeedsRefresh && !alreadyRetried) {
        const newToken = await refreshAccessToken()
        if (newToken) {
          token = newToken
          return attempt(true)
        }
      }
      handlers.onFatalError(err instanceof Error ? err.message : 'Connection lost')
    }
  }

  await attempt(false)
}
