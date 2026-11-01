import { useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQueryClient } from '@tanstack/react-query'
import api from '../../api/axiosInstance'
import { useAppDispatch } from '../../hooks'
import { clearCredentials } from './authSlice'

/** Revokes the refresh cookie, forgets the access token and cached data, and goes to sign-in. */
export function useSignOut() {
  const dispatch = useAppDispatch()
  const navigate = useNavigate()
  const queryClient = useQueryClient()

  return useCallback(async () => {
    await api.post('/auth/logout').catch(() => null)
    dispatch(clearCredentials())
    queryClient.clear()
    navigate('/login')
  }, [dispatch, navigate, queryClient])
}
