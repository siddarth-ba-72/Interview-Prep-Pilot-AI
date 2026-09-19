import { configureStore } from '@reduxjs/toolkit'
import authReducer from './features/auth/authSlice'
import chatReducer from './features/chat/chatSlice'
import interviewReducer from './features/interviews/interviewSlice'
import testReducer from './features/tests/testSlice'

export const store = configureStore({
  reducer: {
    auth: authReducer,
    chat: chatReducer,
    interviews: interviewReducer,
    tests: testReducer,
  },
})

export type RootState = ReturnType<typeof store.getState>
export type AppDispatch = typeof store.dispatch
