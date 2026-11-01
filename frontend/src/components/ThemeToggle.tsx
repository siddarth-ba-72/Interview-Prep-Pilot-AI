import { Moon, Sun } from 'lucide-react'
import { useTheme } from '../features/theme/ThemeProvider'
import { buttonClass } from './ui/Button'

export default function ThemeToggle() {
  const { theme, toggleTheme } = useTheme()
  const label = theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'

  return (
    <button
      type="button"
      onClick={toggleTheme}
      aria-label={label}
      title={label}
      className={buttonClass({ variant: 'quiet', size: 'sm', className: 'w-8 px-0' })}
    >
      {theme === 'dark' ? <Sun size={16} /> : <Moon size={16} />}
    </button>
  )
}
