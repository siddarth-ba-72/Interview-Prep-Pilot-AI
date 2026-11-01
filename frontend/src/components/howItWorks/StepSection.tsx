import { useRef, useState, type ReactNode } from 'react'
import type { Scene, Step } from '../../features/howItWorks/content'
import { useInView, usePrefersReducedMotion } from '../../features/howItWorks/hooks'
import Reveal from './Reveal'
import ShotFrame from './ShotFrame'

const SCENE_MS = 6500

/**
 * One step of the guide: a heading, the step's scenes as a list to pick from, and the screenshot of
 * the selected scene. Scenes advance on their own while the step is on screen, until the reader picks one.
 */
export default function StepSection({
  step,
  reverse = false,
  onOpen,
  extra,
}: {
  step: Step
  reverse?: boolean
  onOpen: (scenes: Scene[], index: number) => void
  extra?: ReactNode
}) {
  const [active, setActive] = useState(0)
  const [autoplay, setAutoplay] = useState(true)
  const [hovered, setHovered] = useState(false)
  const galleryRef = useRef<HTMLDivElement>(null)
  const inView = useInView(galleryRef, { rootMargin: '-15% 0px -15% 0px' })
  const reducedMotion = usePrefersReducedMotion()
  const playing = autoplay && !reducedMotion && step.scenes.length > 1

  function select(index: number) {
    setActive(index)
    setAutoplay(false)
  }

  return (
    <section id={step.id} aria-labelledby={`${step.id}-title`} className="scroll-mt-28">
      <Reveal>
        <h2 id={`${step.id}-title`} className="max-w-3xl text-[28px] font-semibold leading-[1.15] tracking-[-0.018em] text-ink text-balance sm:text-[32px]">
          {step.title}
        </h2>
        <p className="mt-3 max-w-2xl text-base leading-[1.6] text-graphite text-pretty">{step.lead}</p>
      </Reveal>

      <div
        ref={galleryRef}
        onMouseEnter={() => setHovered(true)}
        onMouseLeave={() => setHovered(false)}
        className="mt-8 grid items-start gap-8 lg:grid-cols-12 lg:gap-12"
      >
        <Reveal className={`lg:col-span-7 ${reverse ? 'lg:order-1' : 'lg:order-2'}`}>
          <ShotFrame scenes={step.scenes} active={active} onOpen={(index) => onOpen(step.scenes, index)} />
        </Reveal>

        <Reveal className={`lg:col-span-5 ${reverse ? 'lg:order-2' : 'lg:order-1'}`}>
          <ol className="border-t border-line">
            {step.scenes.map((scene, i) => {
              const selected = i === active
              return (
                <li key={scene.title} className="border-b border-line">
                  <button
                    type="button"
                    onClick={() => select(i)}
                    aria-current={selected ? 'step' : undefined}
                    className="relative w-full py-3.5 text-left"
                  >
                    <span className={`block text-[15px] transition-colors ${selected ? 'font-medium text-ink' : 'text-graphite hover:text-ink'}`}>
                      {scene.title}
                    </span>
                    <span
                      className={`grid transition-[grid-template-rows,opacity] duration-300 ease-out ${
                        selected ? 'grid-rows-[1fr] opacity-100' : 'grid-rows-[0fr] opacity-0'
                      }`}
                    >
                      <span className="overflow-hidden">
                        <span className="type-body block pt-1 text-graphite">{scene.body}</span>
                      </span>
                    </span>
                    {selected && playing && (
                      <span
                        key={active}
                        aria-hidden
                        onAnimationEnd={() => setActive((current) => (current + 1) % step.scenes.length)}
                        className="animate-progress absolute inset-x-0 -bottom-px h-0.5 bg-ballpoint"
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
            <ul className="mt-6 flex flex-col gap-3">
              {step.tips.map((tip) => (
                <li key={tip} className="border-l-2 border-edge pl-3.5 text-sm leading-[1.55] text-ink">
                  {tip}
                </li>
              ))}
            </ul>
          )}
        </Reveal>
      </div>

      {extra && <Reveal className="mt-10">{extra}</Reveal>}
    </section>
  )
}
