import { useEffect, useState, type RefObject } from 'react'

/** True while the element is on screen (or, with `once`, from the first time it is seen). */
export function useInView(
  ref: RefObject<Element>,
  { once = false, rootMargin = '0px' }: { once?: boolean; rootMargin?: string } = {}
): boolean {
  const [inView, setInView] = useState(false)

  useEffect(() => {
    const el = ref.current
    if (!el) return
    if (typeof IntersectionObserver === 'undefined') {
      setInView(true)
      return
    }
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setInView(true)
          if (once) observer.disconnect()
        } else if (!once) {
          setInView(false)
        }
      },
      { rootMargin }
    )
    observer.observe(el)
    return () => observer.disconnect()
  }, [ref, once, rootMargin])

  return inView
}

const REDUCED_MOTION = '(prefers-reduced-motion: reduce)'

export function usePrefersReducedMotion(): boolean {
  const [reduced, setReduced] = useState(() => window.matchMedia?.(REDUCED_MOTION).matches ?? false)

  useEffect(() => {
    const query = window.matchMedia?.(REDUCED_MOTION)
    if (!query) return
    const onChange = () => setReduced(query.matches)
    query.addEventListener('change', onChange)
    return () => query.removeEventListener('change', onChange)
  }, [])

  return reduced
}

/** The id of the section crossing the middle band of the viewport. */
export function useActiveSection(ids: string[]): string | null {
  const [active, setActive] = useState<string | null>(null)
  const key = ids.join('|')

  useEffect(() => {
    if (typeof IntersectionObserver === 'undefined') return
    const observer = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (entry.isIntersecting) setActive(entry.target.id)
        }
      },
      { rootMargin: '-40% 0px -55% 0px' }
    )
    for (const id of key.split('|')) {
      const el = document.getElementById(id)
      if (el) observer.observe(el)
    }
    return () => observer.disconnect()
  }, [key])

  return active
}

/** How far (0 to 1) the reader has scrolled through the element. */
export function useScrollProgress(ref: RefObject<HTMLElement>): number {
  const [progress, setProgress] = useState(0)

  useEffect(() => {
    let frame = 0
    const update = () => {
      frame = 0
      const el = ref.current
      if (!el) return
      const rect = el.getBoundingClientRect()
      const travelled = window.innerHeight * 0.5 - rect.top
      setProgress(Math.min(1, Math.max(0, travelled / rect.height)))
    }
    const onScroll = () => {
      if (!frame) frame = requestAnimationFrame(update)
    }
    update()
    window.addEventListener('scroll', onScroll, { passive: true })
    window.addEventListener('resize', onScroll)
    return () => {
      window.removeEventListener('scroll', onScroll)
      window.removeEventListener('resize', onScroll)
      if (frame) cancelAnimationFrame(frame)
    }
  }, [ref])

  return progress
}

/** Scrolls to a section, smoothly unless the reader prefers reduced motion. */
export function scrollToSection(id: string) {
  const smooth = !(window.matchMedia?.(REDUCED_MOTION).matches ?? false)
  document.getElementById(id)?.scrollIntoView({ behavior: smooth ? 'smooth' : 'auto', block: 'start' })
}
