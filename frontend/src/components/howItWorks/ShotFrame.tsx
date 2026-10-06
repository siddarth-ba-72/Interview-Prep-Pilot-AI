import { Maximize2, ZoomIn } from 'lucide-react'
import { useTheme } from '../../features/theme/ThemeProvider'
import { shotUrl, type Hotspot, type Scene } from '../../features/howItWorks/content'

/**
 * A screenshot in a browser window. All of a step's screenshots are stacked so switching scenes
 * crossfades between them; the active scene's numbered hotspots pop in on top, with their labels in the
 * caption so they never cover the screen they point at. The screenshot follows the theme.
 */
export default function ShotFrame({
  scenes,
  active,
  onOpen,
}: {
  scenes: Scene[]
  active: number
  onOpen: (index: number) => void
}) {
  const { theme } = useTheme()
  const scene = scenes[active]

  return (
    <figure className="group relative m-0">
      <div
        aria-hidden
        className="pointer-events-none absolute -inset-3 rounded-[28px] bg-gradient-to-br from-primary/30 via-accent/20 to-transparent opacity-60 blur-2xl transition-opacity duration-500 group-hover:opacity-100"
      />
      <div className="relative overflow-hidden rounded-2xl border border-border bg-surface shadow-xl shadow-primary/10">
        <div className="flex items-center gap-3 border-b border-border bg-surface-hover/70 px-3 py-2 sm:px-4">
          <div className="flex shrink-0 gap-1.5" aria-hidden>
            <span className="h-2.5 w-2.5 rounded-full bg-[#ff5f57]" />
            <span className="h-2.5 w-2.5 rounded-full bg-[#febc2e]" />
            <span className="h-2.5 w-2.5 rounded-full bg-[#28c840]" />
          </div>
          <div className="flex min-w-0 flex-1 justify-center overflow-hidden">
            <span
              key={scene.where}
              className="animate-word-in truncate rounded-md border border-border bg-bg px-3 py-0.5 text-[11px] font-semibold text-muted"
            >
              PrepPilot › {scene.where}
            </span>
          </div>
          <button
            type="button"
            onClick={() => onOpen(active)}
            aria-label={`Enlarge screenshot: ${scene.title}`}
            className="flex h-7 w-7 shrink-0 items-center justify-center rounded-md text-muted transition-colors hover:bg-surface hover:text-fg"
          >
            <Maximize2 size={14} />
          </button>
        </div>

        <div className="relative aspect-[8/5] overflow-hidden bg-bg">
          {scenes.map((s, i) => (
            <img
              key={`${s.shot}-${i}`}
              src={shotUrl(s.shot, theme)}
              alt={i === active ? `Screenshot: ${s.title}` : ''}
              aria-hidden={i !== active}
              loading="lazy"
              decoding="async"
              width={1600}
              height={1000}
              className={`absolute inset-0 h-full w-full object-cover object-top transition-all duration-700 ease-out ${
                i === active ? 'scale-100 opacity-100' : 'scale-[1.03] opacity-0'
              }`}
            />
          ))}
          <button
            type="button"
            tabIndex={-1}
            aria-hidden
            onClick={() => onOpen(active)}
            className="absolute inset-0 cursor-zoom-in"
          />
          {scene.hotspots?.map((hotspot, i) => (
            <HotspotMarker key={`${active}-${i}`} hotspot={hotspot} number={i + 1} delay={350 + i * 180} />
          ))}
        </div>
      </div>

      <figcaption className="relative mt-3 flex min-h-6 flex-wrap items-center gap-x-4 gap-y-1.5 px-1 text-xs">
        {scene.hotspots?.length ? (
          scene.hotspots.map((hotspot, i) => (
            <span
              key={`${active}-${i}`}
              className="animate-pop-in inline-flex items-center gap-1.5 font-semibold text-fg"
              style={{ animationDelay: `${350 + i * 180}ms` }}
            >
              <span className="flex h-5 w-5 items-center justify-center rounded-full bg-primary text-[10px] font-black text-primary-fg">
                {i + 1}
              </span>
              {hotspot.label}
            </span>
          ))
        ) : (
          <span className="inline-flex items-center gap-1.5 text-muted">
            <ZoomIn size={14} aria-hidden />
            Click the screenshot to see it full size
          </span>
        )}
      </figcaption>
    </figure>
  )
}

function HotspotMarker({ hotspot, number, delay }: { hotspot: Hotspot; number: number; delay: number }) {
  return (
    <span
      aria-hidden
      className="pointer-events-none absolute z-10 animate-pop-in"
      style={{ left: `${hotspot.x}%`, top: `${hotspot.y}%`, animationDelay: `${delay}ms` }}
    >
      <span className="absolute -left-3 -top-3 flex h-6 w-6 items-center justify-center">
        <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-primary/50 motion-reduce:animate-none" />
        <span className="relative flex h-6 w-6 items-center justify-center rounded-full bg-primary text-[11px] font-black text-primary-fg ring-4 ring-primary/25">
          {number}
        </span>
      </span>
    </span>
  )
}
