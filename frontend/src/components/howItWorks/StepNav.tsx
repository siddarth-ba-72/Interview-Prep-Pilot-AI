import { useEffect, useRef } from 'react'
import type { LucideIcon } from 'lucide-react'
import { scrollToSection } from '../../features/howItWorks/hooks'

export interface NavItem {
  id: string
  label: string
  icon: LucideIcon
}

/** Sticky chips for every section, with a bar showing how far through the guide the reader is. */
export default function StepNav({ items, active, progress }: { items: NavItem[]; active: string | null; progress: number }) {
  const scrollerRef = useRef<HTMLDivElement>(null)
  const activeIndex = items.findIndex((item) => item.id === active)

  // On narrow screens the chips scroll sideways: keep the active one in view.
  useEffect(() => {
    const scroller = scrollerRef.current
    const chip = scroller?.querySelector<HTMLElement>(`[data-section="${active}"]`)
    if (!scroller || !chip || scroller.scrollWidth <= scroller.clientWidth) return
    scroller.scrollTo({ left: chip.offsetLeft - scroller.clientWidth / 2 + chip.clientWidth / 2, behavior: 'smooth' })
  }, [active])

  return (
    <nav aria-label="Guide sections" className="sticky top-16 z-10 border-b border-border bg-surface/85 backdrop-blur-md">
      <div
        ref={scrollerRef}
        className="relative mx-auto flex max-w-6xl gap-1 overflow-x-auto px-4 py-2 [scrollbar-width:none] sm:px-6 lg:justify-center lg:px-8"
      >
        {items.map((item, i) => {
          const Icon = item.icon
          const current = i === activeIndex
          const done = activeIndex > i
          return (
            <button
              key={item.id}
              type="button"
              data-section={item.id}
              onClick={() => scrollToSection(item.id)}
              aria-current={current ? 'true' : undefined}
              className={`inline-flex shrink-0 items-center gap-1.5 rounded-full px-3 py-1.5 text-xs font-bold transition-all duration-300 ${
                current
                  ? 'bg-primary text-primary-fg shadow-md shadow-primary/30'
                  : done
                    ? 'text-primary hover:bg-primary-subtle'
                    : 'text-muted hover:bg-surface-hover hover:text-fg'
              }`}
            >
              <Icon size={14} />
              {item.label}
            </button>
          )
        })}
      </div>
      <div className="h-0.5 bg-border/50" aria-hidden>
        <div
          className="h-full origin-left bg-gradient-to-r from-primary to-accent"
          style={{ transform: `scaleX(${progress})` }}
        />
      </div>
    </nav>
  )
}
