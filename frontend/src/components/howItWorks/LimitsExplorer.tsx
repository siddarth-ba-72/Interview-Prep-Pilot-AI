import { useEffect, useRef, useState, type ReactNode } from 'react'
import { CircleCheck, Infinity as InfinityIcon, Lock, RotateCcw, Zap } from 'lucide-react'
import { formatAvailableAt } from '../../api/usage'
import {
  ALWAYS_FREE,
  COSTS_A_USE,
  LIMIT_ACTIONS,
  TIERS,
  type LimitKey,
} from '../../features/howItWorks/content'
import { usePrefersReducedMotion } from '../../features/howItWorks/hooks'

type Tier = keyof typeof TIERS

const WINDOW_MS = 24 * 60 * 60 * 1000

export default function LimitsExplorer() {
  const [tier, setTier] = useState<Tier>('student')

  return (
    <div className="flex flex-col gap-5">
      <div className="grid gap-5 lg:grid-cols-5">
        <div className="rounded-2xl border border-border bg-surface p-5 sm:p-6 lg:col-span-3">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <h3 className="text-sm font-bold text-fg">Your daily allowance</h3>
            <TierToggle tier={tier} onChange={setTier} />
          </div>
          <p className="mt-1 text-xs text-muted">{TIERS[tier].hint}</p>
          <dl className="mt-5 grid grid-cols-2 gap-3 sm:grid-cols-4">
            {LIMIT_ACTIONS.map((action) => (
              <LimitTile key={action.key} label={action.label} unit={action.unit} value={TIERS[tier].limits[action.key]} />
            ))}
          </dl>
          <p className="mt-4 text-xs leading-relaxed text-muted">
            Each limit counts your uses over the last 24 hours. Use the last one and that action locks, then the full
            limit comes back 24 hours after that last use.
          </p>
        </div>

        <LimitSimulator tier={tier} />
      </div>

      <div className="grid gap-5 md:grid-cols-2">
        <RuleList
          title="Uses one from your limit"
          items={COSTS_A_USE}
          icon={<Zap size={15} />}
          tone="border-warning/30 bg-warning-subtle text-warning-fg"
        />
        <RuleList
          title="Always free"
          items={ALWAYS_FREE}
          icon={<CircleCheck size={15} />}
          tone="border-success/30 bg-success-subtle text-success-fg"
        />
      </div>

      <p className="flex items-start gap-2.5 rounded-xl border border-border bg-surface px-4 py-3 text-sm text-fg">
        <RotateCcw size={16} className="mt-0.5 shrink-0 text-primary" aria-hidden />
        If the AI fails to answer, start a test or start an interview, you get that use back automatically.
      </p>
    </div>
  )
}

function TierToggle({ tier, onChange }: { tier: Tier; onChange: (tier: Tier) => void }) {
  return (
    <div className="relative grid grid-cols-2 rounded-full bg-surface-hover p-1 text-xs font-bold">
      <span
        aria-hidden
        className={`absolute inset-y-1 left-1 w-[calc(50%-0.25rem)] rounded-full bg-primary shadow-md shadow-primary/30 transition-transform duration-300 ease-out ${
          tier === 'standard' ? 'translate-x-full' : 'translate-x-0'
        }`}
      />
      {(Object.keys(TIERS) as Tier[]).map((key) => (
        <button
          key={key}
          type="button"
          aria-pressed={tier === key}
          onClick={() => onChange(key)}
          className={`relative rounded-full px-3.5 py-1.5 transition-colors ${
            tier === key ? 'text-primary-fg' : 'text-muted hover:text-fg'
          }`}
        >
          {TIERS[key].label}
        </button>
      ))}
    </div>
  )
}

function LimitTile({ label, unit, value }: { label: string; unit: string; value: number | null }) {
  const shown = useCountUp(value ?? 0)
  return (
    <div className="flex flex-col rounded-xl border border-border bg-bg px-4 py-3">
      <dt className="text-[11px] font-semibold uppercase tracking-wide text-muted">{label}</dt>
      <dd className="mt-auto pt-1">
        {value === null ? (
          <span className="flex h-8 items-center text-primary" aria-label="No limit">
            <InfinityIcon size={26} strokeWidth={2.5} />
          </span>
        ) : (
          <span className="block text-2xl font-extrabold tabular-nums text-fg">{shown}</span>
        )}
        <span className="text-xs text-muted">{value === null ? 'no limit' : unit}</span>
      </dd>
    </div>
  )
}

/** Animates a number from its previous value to `target`. */
function useCountUp(target: number, ms = 600): number {
  const reducedMotion = usePrefersReducedMotion()
  const [value, setValue] = useState(target)
  const from = useRef(target)

  useEffect(() => {
    if (reducedMotion) {
      from.current = target
      setValue(target)
      return
    }
    const start = from.current
    const t0 = performance.now()
    let frame = requestAnimationFrame(function step(now) {
      const p = Math.min(1, (now - t0) / ms)
      const eased = 1 - Math.pow(1 - p, 3)
      const next = Math.round(start + (target - start) * eased)
      from.current = next
      setValue(next)
      if (p < 1) frame = requestAnimationFrame(step)
    })
    return () => cancelAnimationFrame(frame)
  }, [target, ms, reducedMotion])

  return value
}

const SIMULATED: Array<{ key: Exclude<LimitKey, 'topics'>; label: string }> = [
  { key: 'mockInterviews', label: 'Mock interviews' },
  { key: 'tests', label: 'Tests' },
  { key: 'learnMessages', label: 'Learn messages' },
]

/** A pretend usage tile, styled like the dashboard's, that locks when its limit is used up. */
function LimitSimulator({ tier }: { tier: Tier }) {
  const [action, setAction] = useState<(typeof SIMULATED)[number]['key']>('mockInterviews')
  const [used, setUsed] = useState(0)
  const [lockedUntil, setLockedUntil] = useState<string | null>(null)
  const limit = TIERS[tier].limits[action] ?? 0
  const remaining = limit - used
  const locked = remaining <= 0
  const label = SIMULATED.find((s) => s.key === action)?.label ?? ''

  useEffect(() => {
    setUsed(0)
    setLockedUntil(null)
  }, [tier, action])

  function spendOne() {
    if (locked) return
    setUsed(used + 1)
    if (remaining === 1) setLockedUntil(new Date(Date.now() + WINDOW_MS).toISOString())
  }

  function reset() {
    setUsed(0)
    setLockedUntil(null)
  }

  return (
    <div className="flex flex-col rounded-2xl border border-border bg-surface p-5 sm:p-6 lg:col-span-2">
      <h3 className="text-sm font-bold text-fg">Try it: watch a limit lock</h3>
      <div className="mt-3 flex flex-wrap gap-1.5">
        {SIMULATED.map((s) => (
          <button
            key={s.key}
            type="button"
            aria-pressed={action === s.key}
            onClick={() => setAction(s.key)}
            className={`rounded-full border px-3 py-1 text-xs font-semibold transition-colors ${
              action === s.key
                ? 'border-primary bg-primary-subtle text-primary'
                : 'border-border text-muted hover:bg-surface-hover hover:text-fg'
            }`}
          >
            {s.label}
          </button>
        ))}
      </div>

      <div
        aria-live="polite"
        className={`mt-4 rounded-xl border px-4 py-3 transition-colors duration-300 ${
          locked ? 'border-danger/30 bg-danger-subtle' : 'border-border bg-bg'
        }`}
      >
        <p className="flex items-center justify-between text-[11px] font-semibold uppercase tracking-wide text-muted">
          {label}
          {locked && <Lock size={13} className="text-danger-fg" aria-hidden />}
        </p>
        <p
          key={remaining}
          className={`animate-pop-in mt-1 text-2xl font-extrabold leading-none tabular-nums ${
            locked ? 'text-danger-fg' : 'text-fg'
          }`}
        >
          {Math.max(0, remaining)}
        </p>
        <p className={`mt-1 text-xs ${locked ? 'text-danger-fg' : 'text-muted'}`}>
          {locked && lockedUntil ? `Back ${formatAvailableAt(lockedUntil)}` : `of ${limit} left`}
        </p>
        <div className="mt-3 h-1.5 overflow-hidden rounded-full bg-surface-hover">
          <div
            className={`h-full rounded-full transition-all duration-500 ease-out ${
              locked ? 'bg-danger' : 'bg-gradient-to-r from-primary to-accent'
            }`}
            style={{ width: `${limit ? (Math.max(0, remaining) / limit) * 100 : 0}%` }}
          />
        </div>
      </div>

      <p className="mt-3 min-h-10 text-xs leading-relaxed text-muted">
        {locked
          ? `That was the last one, so it locks. 24 hours after that use, all ${limit} come back at once.`
          : used === 0
            ? 'Press Use one to spend a use, just like starting the real thing.'
            : `${remaining} left. Each use counts for 24 hours.`}
      </p>

      <div className="mt-auto flex gap-2 pt-3">
        <button
          type="button"
          onClick={spendOne}
          disabled={locked}
          className="flex-1 rounded-lg bg-primary py-2 text-xs font-bold text-primary-fg transition-colors hover:bg-primary-hover disabled:cursor-not-allowed disabled:opacity-50"
        >
          Use one
        </button>
        <button
          type="button"
          onClick={reset}
          className="rounded-lg border border-border px-3 py-2 text-xs font-semibold text-muted transition-colors hover:bg-surface-hover hover:text-fg"
        >
          Reset
        </button>
      </div>
    </div>
  )
}

function RuleList({
  title,
  items,
  icon,
  tone,
}: {
  title: string
  items: string[]
  icon: ReactNode
  tone: string
}) {
  return (
    <div className="rounded-2xl border border-border bg-surface p-5 sm:p-6">
      <h3 className="text-sm font-bold text-fg">{title}</h3>
      <ul className="mt-3 flex flex-col gap-2">
        {items.map((item) => (
          <li key={item} className="flex items-center gap-2.5 text-sm text-fg">
            <span className={`flex h-6 w-6 shrink-0 items-center justify-center rounded-full border ${tone}`} aria-hidden>
              {icon}
            </span>
            {item}
          </li>
        ))}
      </ul>
    </div>
  )
}
