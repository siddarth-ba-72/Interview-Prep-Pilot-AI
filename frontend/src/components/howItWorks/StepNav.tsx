import { useEffect, useRef } from 'react'
import { scrollToSection } from '../../features/howItWorks/hooks'

export interface NavItem {
  id: string
  label: string
}

/** The guide's sections as a sticky row of links, with a line showing how far through the reader is. */
export default function StepNav({ items, active, progress }: { items: NavItem[]; active: string | null; progress: number }) {
  const scrollerRef = useRef<HTMLDivElement>(null)

  // On narrow screens the links scroll sideways: keep the active one in view.
  useEffect(() => {
    const scroller = scrollerRef.current
    const link = scroller?.querySelector<HTMLElement>(`[data-section="${active}"]`)
    if (!scroller || !link || scroller.scrollWidth <= scroller.clientWidth) return
    scroller.scrollTo({ left: link.offsetLeft - scroller.clientWidth / 2 + link.clientWidth / 2, behavior: 'smooth' })
  }, [active])

  return (
    <nav aria-label="Guide sections" className="sticky top-[53px] z-20 border-b border-line bg-paper">
      <div
        ref={scrollerRef}
        className="mx-auto flex w-full max-w-[1200px] gap-6 overflow-x-auto px-4 [scrollbar-width:none] sm:px-6 lg:px-8"
      >
        {items.map((item) => {
          const current = item.id === active
          return (
            <button
              key={item.id}
              type="button"
              data-section={item.id}
              onClick={() => scrollToSection(item.id)}
              aria-current={current ? 'true' : undefined}
              className={`shrink-0 py-3 text-sm transition-colors duration-150 ${
                current ? 'font-medium text-ink' : 'text-graphite hover:text-ink'
              }`}
            >
              {item.label}
            </button>
          )
        })}
      </div>
      <div className="h-0.5" aria-hidden>
        <div className="h-full origin-left bg-ballpoint" style={{ transform: `scaleX(${progress})` }} />
      </div>
    </nav>
  )
}
