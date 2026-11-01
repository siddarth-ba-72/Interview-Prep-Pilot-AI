import { Maximize2 } from 'lucide-react'
import { useTheme } from '../../features/theme/ThemeProvider'
import { shotUrl, type Scene } from '../../features/howItWorks/content'

/**
 * A step's screenshots, stacked so switching scenes crossfades between them. The frame is a plain
 * 1px edge; the caption says where the screen lives in the app. Screenshots follow the theme.
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
    <figure className="m-0">
      <button
        type="button"
        onClick={() => onOpen(active)}
        aria-label={`Enlarge screenshot: ${scene.title}`}
        className="group relative block aspect-[8/5] w-full cursor-zoom-in overflow-hidden rounded-lg border border-line bg-sheet"
      >
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
            className={`absolute inset-0 h-full w-full object-cover object-top transition-opacity duration-500 ease-out ${
              i === active ? 'opacity-100' : 'opacity-0'
            }`}
          />
        ))}
        <span className="absolute right-3 top-3 flex h-8 w-8 items-center justify-center rounded-md border border-line bg-sheet text-graphite opacity-0 transition-opacity duration-150 group-hover:opacity-100 group-focus-visible:opacity-100">
          <Maximize2 size={14} aria-hidden />
        </span>
      </button>
      <figcaption className="type-meta mt-2.5">PrepPilot › {scene.where}</figcaption>
    </figure>
  )
}
