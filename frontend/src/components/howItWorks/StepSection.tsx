import { useRef, useState, type ReactNode } from 'react'
import { Lightbulb } from 'lucide-react'
import type { Scene, Step } from '../../features/howItWorks/content'
import { useInView, usePrefersReducedMotion } from '../../features/howItWorks/hooks'
import Reveal from './Reveal'
import ShotFrame from './ShotFrame'

const SCENE_MS = 6500

/**
 * One step of the guide: a heading, the step's scenes as a clickable list, and the screenshot of the
 * selected scene. Scenes advance on their own while the step is on screen, until the reader picks one.
 */
export default function StepSection({
  step,
  number,
  reverse = false,
  onOpen,
  extra,
  extraFirst = false,
}: {
  step: Step
  number: number
  reverse?: boolean
  onOpen: (scenes: Scene[], index: number) => void
  extra?: ReactNode
  extraFirst?: boolean
}) {
  const [active, setActive] = useState(0)
  const [autoplay, setAutoplay] = useState(true)
  const [hovered, setHovered] = useState(false)
  const galleryRef = useRef<HTMLDivElement>(null)
  const inView = useInView(galleryRef, { rootMargin: '-15% 0px -15% 0px' })
  const reducedMotion = usePrefersReducedMotion()
  const playing = autoplay && !reducedMotion && step.scenes.length > 1
  const Icon = step.icon

  function select(index: number) {
    setActive(index)
    setAutoplay(false)
  }

  const extraBlock = extra && <Reveal className={extraFirst ? 'mt-8' : 'mt-10'}>{extra}</Reveal>

  return (
    <section id={step.id} aria-labelledby={`${step.id}-title`} className="scroll-mt-32">
      <Reveal>
        <div className="flex items-start gap-4 sm:gap-5">
          <span className="relative flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl bg-gradient-to-br from-primary to-accent text-white shadow-lg shadow-primary/30 sm:h-14 sm:w-14">
            <Icon size={24} />
            <span className="absolute -right-2 -top-2 flex h-6 min-w-6 items-center justify-center rounded-full border-2 border-bg bg-fg px-1 text-[11px] font-black text-bg">
              {number}
            </span>
          </span>
          <div className="min-w-0">
            <p className="text-xs font-bold uppercase tracking-[0.18em] text-primary">
              Step {number} · {step.nav}
            </p>
            <h2 id={`${step.id}-title`} className="mt-1.5 text-2xl font-extrabold tracking-tight text-fg sm:text-3xl">
              {step.title}
            </h2>
            <p className="mt-2 max-w-2xl text-base leading-relaxed text-muted">{step.lead}</p>
          </div>
        </div>
      </Reveal>

      {extraFirst && extraBlock}

      <div
        ref={galleryRef}
        onMouseEnter={() => setHovered(true)}
        onMouseLeave={() => setHovered(false)}
        className="mt-8 grid items-start gap-6 lg:grid-cols-12 lg:gap-10"
      >
        <Reveal delay={120} className={`lg:col-span-7 ${reverse ? 'lg:order-1' : 'lg:order-2'}`}>
          <ShotFrame scenes={step.scenes} active={active} onOpen={(index) => onOpen(step.scenes, index)} />
        </Reveal>

        <Reveal delay={220} className={`lg:col-span-5 ${reverse ? 'lg:order-2' : 'lg:order-1'}`}>
          <ol className="flex flex-col gap-1.5">
            {step.scenes.map((scene, i) => {
              const selected = i === active
              return (
                <li key={scene.title}>
                  <button
                    type="button"
                    onClick={() => select(i)}
                    aria-current={selected ? 'step' : undefined}
                    className={`relative w-full overflow-hidden rounded-xl border px-4 py-3 text-left transition-all duration-300 ${
                      selected
                        ? 'border-primary/40 bg-primary-subtle shadow-sm'
                        : 'border-transparent hover:border-border hover:bg-surface'
                    }`}
                  >
                    <span className="flex items-center gap-3">
                      <span
                        className={`flex h-6 w-6 shrink-0 items-center justify-center rounded-full text-[11px] font-bold transition-colors ${
                          selected ? 'bg-primary text-primary-fg' : 'bg-surface-hover text-muted'
                        }`}
                      >
                        {i + 1}
                      </span>
                      <span className={`text-sm font-bold transition-colors ${selected ? 'text-fg' : 'text-muted'}`}>
                        {scene.title}
                      </span>
                    </span>
                    <span
                      className={`grid transition-all duration-300 ease-out ${
                        selected ? 'grid-rows-[1fr] opacity-100' : 'grid-rows-[0fr] opacity-0'
                      }`}
                    >
                      <span className="overflow-hidden pl-9 text-sm leading-relaxed text-muted">
                        <span className="block pt-1.5">{scene.body}</span>
                      </span>
                    </span>
                    {selected && playing && (
                      <span
                        key={active}
                        aria-hidden
                        onAnimationEnd={() => setActive((current) => (current + 1) % step.scenes.length)}
                        className="animate-grow-x absolute inset-x-0 bottom-0 h-0.5 bg-gradient-to-r from-primary to-accent"
                        style={{
                          animationDuration: `${SCENE_MS}ms`,
                          animationPlayState: inView && !hovered ? 'running' : 'paused',
                        }}
                      />
                    )}
                  </button>
                </li>
              )
            })}
          </ol>

          {step.tips.length > 0 && (
            <ul className="mt-5 flex flex-col gap-2.5">
              {step.tips.map((tip) => (
                <li
                  key={tip}
                  className="flex gap-2.5 rounded-xl border border-border bg-surface px-3.5 py-3 text-sm leading-relaxed text-fg"
                >
                  <Lightbulb size={16} className="mt-0.5 shrink-0 text-warning" aria-hidden />
                  {tip}
                </li>
              ))}
            </ul>
          )}
        </Reveal>
      </div>

      {!extraFirst && extraBlock}
    </section>
  )
}
