import { useEffect, useState } from 'react'
import { Infinity as InfinityIcon, UserRoundPen } from 'lucide-react'
import { TRACKS, type TrackKey } from '../features/prepTrack/tracks'

interface PrepTrackExplorerProps {
  /** The viewer's own track. When set, it is selected first and marked "Your track". */
  current?: TrackKey
  /** Labels for the viewer's profile answers, shown as chips (e.g. "College student", "Backend"). */
  profileChips?: string[]
  /** Shown as a button when the viewer previews the track that is not theirs. */
  onEditProfile?: () => void
}

/** Shows how Learn, Test and Mock Interview adapt to the experience answer, with a toggle to compare the two tracks. */
export default function PrepTrackExplorer({ current, profileChips = [], onEditProfile }: PrepTrackExplorerProps) {
  const [selected, setSelected] = useState<TrackKey>(current ?? 'placement')
  // The profile can arrive after the first render (session refresh) or change; show the viewer's own track then
  useEffect(() => {
    if (current) setSelected(current)
  }, [current])
  const track = TRACKS[selected]
  const TrackIcon = track.icon
  const previewingOther = current !== undefined && selected !== current

  return (
    <section
      aria-label="Your prep track"
      className="relative overflow-hidden rounded-3xl border border-border bg-surface p-5 sm:p-6"
    >
      <div
        aria-hidden
        className="pointer-events-none absolute -right-24 -top-24 h-64 w-64 rounded-full bg-gradient-to-br from-primary/15 to-accent/15 blur-3xl"
      />

      <div className="relative flex flex-wrap items-start justify-between gap-4">
        <div className="flex min-w-0 items-start gap-3">
          <span
            key={selected}
            className="animate-pop-in flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl bg-gradient-to-br from-primary to-accent text-white shadow-md shadow-primary/30"
          >
            <TrackIcon size={20} />
          </span>
          <div className="min-w-0">
            <h2 className="flex flex-wrap items-center gap-2 text-base font-bold text-fg">
              {!current ? 'Two tracks, one app' : previewingOther ? `${track.label} track` : 'Your prep track'}
              <span className="inline-flex items-center gap-1 rounded-full border border-success/30 bg-success-subtle px-2 py-0.5 text-[11px] font-bold text-success-fg">
                <InfinityIcon size={13} strokeWidth={2.5} aria-hidden />
                Unlimited practice
              </span>
            </h2>
            <p className="mt-0.5 text-xs text-muted">{track.audience}</p>
            {profileChips.length > 0 && !previewingOther && (
              <div className="mt-2 flex flex-wrap gap-1.5">
                {profileChips.map((chip) => (
                  <span
                    key={chip}
                    className="rounded-full border border-border bg-bg px-2.5 py-0.5 text-[11px] font-semibold text-muted"
                  >
                    {chip}
                  </span>
                ))}
              </div>
            )}
          </div>
        </div>
        <TrackToggle selected={selected} current={current} onChange={setSelected} />
      </div>

      <ul className="relative mt-5 grid gap-3 sm:grid-cols-3">
        {track.modes.map(({ icon: Icon, title, body }, i) => (
          <li
            key={`${selected}-${title}`}
            style={{ animationDelay: `${i * 70}ms` }}
            className="animate-rise-in group rounded-2xl border border-border bg-bg p-4 transition-all hover:-translate-y-0.5 hover:border-primary/40 hover:shadow-lg hover:shadow-primary/10"
          >
            <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-primary-subtle text-primary transition-transform group-hover:scale-110 group-hover:-rotate-6">
              <Icon size={17} />
            </span>
            <h3 className="mt-3 text-sm font-bold text-fg">{title}</h3>
            <p className="mt-1 text-xs leading-relaxed text-muted">{body}</p>
          </li>
        ))}
      </ul>

      <div className="relative mt-4 flex min-h-9 flex-wrap items-center justify-between gap-3">
        <p className="text-xs text-muted" aria-live="polite">
          {previewingOther
            ? `You are previewing the ${track.label} track. It follows the experience you pick in your profile.`
            : 'No daily limits: learn, test and interview as much as you like.'}
        </p>
        {previewingOther && onEditProfile && (
          <button
            type="button"
            onClick={onEditProfile}
            className="inline-flex h-9 items-center gap-1.5 rounded-lg border border-border px-3 text-xs font-semibold text-muted transition-colors hover:bg-surface-hover hover:text-fg"
          >
            <UserRoundPen size={14} />
            Change in Profile
          </button>
        )}
      </div>
    </section>
  )
}

function TrackToggle({
  selected,
  current,
  onChange,
}: {
  selected: TrackKey
  current?: TrackKey
  onChange: (track: TrackKey) => void
}) {
  const keys = Object.keys(TRACKS) as TrackKey[]
  return (
    <div className="relative grid shrink-0 grid-cols-2 rounded-full bg-surface-hover p-1 text-xs font-bold">
      <span
        aria-hidden
        className={`absolute inset-y-1 left-1 w-[calc(50%-0.25rem)] rounded-full bg-primary shadow-md shadow-primary/30 transition-transform duration-300 ease-out ${
          selected === keys[1] ? 'translate-x-full' : 'translate-x-0'
        }`}
      />
      {keys.map((key) => (
        <button
          key={key}
          type="button"
          aria-pressed={selected === key}
          onClick={() => onChange(key)}
          className={`relative flex items-center justify-center gap-1 rounded-full px-3.5 py-1.5 transition-colors ${
            selected === key ? 'text-primary-fg' : 'text-muted hover:text-fg'
          }`}
        >
          {TRACKS[key].label}
          {key === current && (
            <span
              aria-label="(your track)"
              className={`h-1.5 w-1.5 rounded-full ${selected === key ? 'bg-primary-fg' : 'bg-primary'}`}
            />
          )}
        </button>
      ))}
    </div>
  )
}
