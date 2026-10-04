import React from 'react'
import ReactDOM from 'react-dom/client'
import { Provider } from 'react-redux'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import App from './App'
import Footer from './components/Footer'
import { store } from './store'
import { ThemeProvider } from './features/theme/ThemeProvider'
import './index.css'

const queryClient = new QueryClient()

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <ThemeProvider>
      <Provider store={store}>
        <QueryClientProvider client={queryClient}>
          <div className="flex min-h-screen flex-col">
            <div className="flex-1 [&_.min-h-screen]:min-h-[calc(100vh-4rem)]">
              <App />
            </div>
            <Footer />
          </div>
        </QueryClientProvider>
      </Provider>
    </ThemeProvider>
  </React.StrictMode>
)
