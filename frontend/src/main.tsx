import React from 'react'
import ReactDOM from 'react-dom/client'
import { Provider } from 'react-redux'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import '@fontsource-variable/ibm-plex-sans/index.css'
import '@fontsource-variable/ibm-plex-sans/wght-italic.css'
import '@fontsource/ibm-plex-serif/400.css'
import '@fontsource/ibm-plex-serif/500.css'
import '@fontsource/ibm-plex-mono/400.css'
import App from './App'
import Footer from './components/Footer'
import { store } from './store'
import { ThemeProvider } from './features/theme/ThemeProvider'
import { initClarity } from './features/analytics/clarity'
import './index.css'

initClarity()

const queryClient = new QueryClient()

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <ThemeProvider>
      <Provider store={store}>
        <QueryClientProvider client={queryClient}>
          <div className="flex min-h-screen flex-col">
            {/* Pages that fill the screen leave room for the 49px footer */}
            <div className="flex-1 [&_.min-h-screen]:min-h-[calc(100vh-49px)]">
              <App />
            </div>
            <Footer />
          </div>
        </QueryClientProvider>
      </Provider>
    </ThemeProvider>
  </React.StrictMode>
)
