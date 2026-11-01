import { useEffect, useRef, type ReactNode } from 'react'
import { createPortal } from 'react-dom'

/**
 * A centred modal. Rendered in a portal so no ancestor's stacking context clips it. Escape and a
 * click on the backdrop close it; focus returns to whatever opened it.
 */
export default function Dialog({
  labelledBy,
  onClose,
  children,
  mask = false,
  className = '',
}: {
  labelledBy: string
  onClose: () => void
  children: ReactNode
  /** Hide the contents from analytics recordings. */
  mask?: boolean
  className?: string
}) {
  const panelRef = useRef<HTMLDivElement>(null)
  const onCloseRef = useRef(onClose)
  onCloseRef.current = onClose

  // Once per opening: a re-render while typing must not move focus
  useEffect(() => {
    const opener = document.activeElement as HTMLElement | null
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') onCloseRef.current()
    }
    window.addEventListener('keydown', onKeyDown)
    // Focus the panel unless something inside asked for focus already (autoFocus)
    if (!panelRef.current?.contains(document.activeElement)) panelRef.current?.focus()
    return () => {
      window.removeEventListener('keydown', onKeyDown)
      opener?.focus?.()
    }
  }, [])

  return createPortal(
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4" onClick={onClose}>
      <div
        ref={panelRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby={labelledBy}
        tabIndex={-1}
        data-clarity-mask={mask ? 'True' : undefined}
        onClick={(event) => event.stopPropagation()}
        className={`animate-dialog-in w-full max-w-lg rounded-lg border border-line bg-sheet p-6 shadow-[0_16px_40px_-12px_rgba(0,0,0,0.28)] outline-none ${className}`}
      >
        {children}
      </div>
    </div>,
    document.body
  )
}
