import { useEffect, useRef } from 'react'
import { ChevronLeft, ChevronRight, X } from 'lucide-react'
import { useTheme } from '../../features/theme/ThemeProvider'
import { shotUrl, type Scene } from '../../features/howItWorks/content'

/** Full-screen view of a step's screenshots. Arrow keys move between them, Escape closes. */
export default function Lightbox({
  scenes,
  index,
  onIndexChange,
  onClose,
}: {
  scenes: Scene[]
  index: number
  onIndexChange: (index: number) => void
  onClose: () => void
}) {
  const { theme } = useTheme()
  const dialogRef = useRef<HTMLDivElement>(null)
  const closeRef = useRef<HTMLButtonElement>(null)
  const scene = scenes[index]
  const count = scenes.length

  useEffect(() => {
    const opener = document.activeElement as HTMLElement | null
    closeRef.current?.focus()
    const overflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    return () => {
      document.body.style.overflow = overflow
      opener?.focus?.()
    }
  }, [])

  useEffect(() => {
    function onKeyDown(e: KeyboardEvent) {
      if (e.key === 'Escape') onClose()
      else if (e.key === 'ArrowRight' && count > 1) onIndexChange((index + 1) % count)
      else if (e.key === 'ArrowLeft' && count > 1) onIndexChange((index - 1 + count) % count)
      else if (e.key === 'Tab') {
        // Keep focus inside the dialog.
        const buttons = dialogRef.current?.querySelectorAll<HTMLElement>('button')
        if (!buttons?.length) return
        const first = buttons[0]
        const last = buttons[buttons.length - 1]
        if (e.shiftKey && document.activeElement === first) {
          e.preventDefault()
          last.focus()
        } else if (!e.shiftKey && document.activeElement === last) {
          e.preventDefault()
          first.focus()
        }
      }
    }
    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [index, count, onIndexChange, onClose])

  const navButton =
    'absolute top-1/2 flex h-11 w-11 -translate-y-1/2 items-center justify-center rounded-full bg-black/60 text-white shadow-lg ring-1 ring-white/20 backdrop-blur-md transition-colors hover:bg-black/80'

  return (
    <div
      ref={dialogRef}
      role="dialog"
      aria-modal="true"
      aria-label={`Screenshot ${index + 1} of ${count}: ${scene.title}`}
      onClick={onClose}
      className="fixed inset-0 z-50 flex flex-col items-center gap-4 bg-black/85 p-4 backdrop-blur-sm sm:p-6"
    >
      <div className="flex w-full max-w-6xl items-center justify-between">
        <span className="text-sm font-semibold text-white/70">
          {index + 1} / {count}
        </span>
        <button
          ref={closeRef}
          type="button"
          onClick={onClose}
          aria-label="Close"
          className="flex h-10 w-10 items-center justify-center rounded-full bg-white/10 text-white transition-colors hover:bg-white/25"
        >
          <X size={20} />
        </button>
      </div>

      <div className="relative flex min-h-0 w-full max-w-6xl flex-1 items-center justify-center">
        <img
          key={`${scene.shot}-${index}`}
          src={shotUrl(scene.shot, theme)}
          alt={`Screenshot: ${scene.title}`}
          onClick={(e) => e.stopPropagation()}
          className="animate-modal-pop max-h-full max-w-full rounded-xl object-contain shadow-2xl ring-1 ring-white/10"
        />
        {count > 1 && (
          <>
            <button
              type="button"
              aria-label="Previous screenshot"
              onClick={(e) => {
                e.stopPropagation()
                onIndexChange((index - 1 + count) % count)
              }}
              className={`${navButton} left-3`}
            >
              <ChevronLeft size={22} />
            </button>
            <button
              type="button"
              aria-label="Next screenshot"
              onClick={(e) => {
                e.stopPropagation()
                onIndexChange((index + 1) % count)
              }}
              className={`${navButton} right-3`}
            >
              <ChevronRight size={22} />
            </button>
          </>
        )}
      </div>

      <div className="max-w-2xl text-center" onClick={(e) => e.stopPropagation()}>
        <p className="text-base font-bold text-white">{scene.title}</p>
        <p className="mt-1 text-sm leading-relaxed text-white/70">{scene.body}</p>
      </div>
    </div>
  )
}
