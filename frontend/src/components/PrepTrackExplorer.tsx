import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { TRACKS, type TrackKey } from '../features/prepTrack/tracks'

interface PrepTrackExplorerProps {
  /** The viewer's own track. When set, it is selected first and marked as theirs. */
  current?: TrackKey
  /** The viewer's profile answers in words (e.g. "3-5 years", "Backend"). */
  profileChips?: string[]
  /** Shows a link to edit the profile. */
  showProfileLink?: boolean
  /** Lays the three modes side by side, for full-width use. */
  wide?: boolean
}

/** How Learn, Test and Mock interview adapt to the experience answer, with a switch to compare the two tracks. */
export default function PrepTrackExplorer({
  current,
  profileChips = [],
  showProfileLink = false,
  wide = false,
}: PrepTrackExplorerProps) {
  const [selected, setSelected] = useState<TrackKey>(current ?? 'placement')
  // The profile can arrive after the first render (session refresh) or change; show the viewer's own track then
  useEffect(() => {
    if (current) setSelected(current)
  }, [current])
  const track = TRACKS[selected]
  const previewingOther = current !== undefined && selected !== current
  const keys = Object.keys(TRACKS) as TrackKey[]

  return (
    <section aria-label="Your prep track" className="rounded-lg border border-line bg-sheet">
      <div className={`gap-x-6 gap-y-3 px-5 pt-4 ${wide ? 'flex flex-wrap items-start justify-between' : ''}`}>
        <div className="min-w-0">
          <h2 className="type-section">{current ? 'Your prep track' : 'Two prep tracks'}</h2>
          <p className="type-meta mt-0.5 text-pretty">{track.audience}</p>
        </div>

        <div
          role="group"
          aria-label="Prep track"
          className={`grid grid-cols-2 rounded-md bg-wash p-0.5 text-[13px] ${wide ? 'w-full sm:w-72' : 'mt-3'}`}
        >
          {keys.map((key) => (
            <button
              key={key}
              type="button"
              aria-pressed={selected === key}
              onClick={() => setSelected(key)}
              className={`h-8 rounded-[5px] transition-colors duration-150 ${
                selected === key ? 'bg-sheet font-medium text-ink shadow-[0_0_0_1px_var(--line)]' : 'text-graphite hover:text-ink'
              }`}
            >
              {TRACKS[key].label}
              {key === current && <span className="text-pencil"> · yours</span>}
            </button>
          ))}
        </div>
      </div>

      <dl className={`mt-1 px-5 pb-1 ${wide ? 'grid gap-x-8 md:grid-cols-3' : ''}`}>
        {track.modes.map(({ title, body }) => (
          <div
            key={`${selected}-${title}`}
            className={wide ? 'border-b border-rule py-4 last:border-b-0 md:border-b-0' : 'border-b border-rule py-3 last:border-b-0'}
          >
            <dt className="text-sm font-medium text-ink">{title}</dt>
            <dd className="type-body mt-0.5 text-graphite">{body}</dd>
          </div>
        ))}
      </dl>

      <div className="flex flex-wrap items-center justify-between gap-x-3 gap-y-1 border-t border-rule px-5 py-3 text-[13px]" aria-live="polite">
        {previewingOther ? (
          <span className="text-graphite">The track follows the experience in your profile.</span>
        ) : profileChips.length > 0 ? (
          <span className="text-graphite" data-clarity-mask="True">
            {profileChips.join(' · ')}
          </span>
        ) : (
          <span className="text-graphite">No daily limits on any mode.</span>
        )}
        {showProfileLink && (
          <Link to="/onboarding" className="font-medium text-ink underline underline-offset-4 decoration-edge hover:decoration-ink">
            Edit profile
          </Link>
        )}
      </div>
    </section>
  )
}
