import { createSlice, PayloadAction } from '@reduxjs/toolkit'
import type { User } from '../../api/profile'

interface AuthState {
  user: User | null
  accessToken: string | null
  status: 'idle' | 'loading' | 'authenticated' | 'error'
}

const initialState: AuthState = {
  user: null,
  accessToken: null,
  status: 'loading',
}

const authSlice = createSlice({
  name: 'auth',
  initialState,
  reducers: {
    setCredentials(state, action: PayloadAction<{ user: User; accessToken: string }>) {
      state.user = action.payload.user
      state.accessToken = action.payload.accessToken
      state.status = 'authenticated'
    },
    setLoading(state) {
      state.status = 'loading'
    },
    setError(state) {
      state.status = 'error'
    },
    clearCredentials(state) {
      state.user = null
      state.accessToken = null
      state.status = 'idle'
    },
  },
})

export const { setCredentials, setLoading, setError, clearCredentials } = authSlice.actions
export default authSlice.reducer
