import { useEffect } from 'react'
import { useAppDispatch } from '../../hooks'
import { setCredentials, setLoading, clearCredentials } from './authSlice'
import api from '../../api/axiosInstance'

/**
 * On app startup, attempt a silent refresh to recover the session
 * from the HttpOnly refresh token cookie. If it fails, stay logged out.
 */
export function useSilentRefresh() {
  const dispatch = useAppDispatch()

  useEffect(() => {
    dispatch(setLoading())
    api
      .post('/auth/refresh')
      .then((
        { data }: { data: { user: { id: string; email: string; displayName: string }; accessToken: string } }
      ) => {
        dispatch(setCredentials({ user: data.user, accessToken: data.accessToken }))
      })
      .catch(() => {
        dispatch(clearCredentials())
      })
  }, [dispatch])
}
