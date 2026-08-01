import type { ReactNode } from 'react'
import { MessagesSquare, ClipboardCheck, Mic } from 'lucide-react'

const FEATURES = [
  { icon: MessagesSquare, label: 'Learn Mode', desc: 'Chat with an AI tutor on any topic, anytime.' },
  { icon: ClipboardCheck, label: 'Test Mode', desc: 'Auto-generated questions with instant scoring.' },
  { icon: Mic, label: 'Mock Interview', desc: 'Sequential Q&A with real-time evaluation.' },
]

export default function AuthShell({
  title,
  subtitle,
  children,
  footer,
}: {
  title: string
  subtitle?: string
  children: ReactNode
  footer?: ReactNode
}) {
  return (
    <div className="flex min-h-screen w-full bg-bg">
      <div className="relative hidden w-1/2 shrink-0 overflow-hidden bg-gradient-to-br from-primary via-primary to-accent lg:flex lg:flex-col lg:justify-between lg:p-12">
        <div className="pointer-events-none absolute -left-24 -top-24 h-72 w-72 rounded-full bg-white/10 blur-3xl" />
        <div className="pointer-events-none absolute bottom-0 right-0 h-96 w-96 translate-x-1/3 translate-y-1/3 rounded-full bg-black/10 blur-3xl" />
        <div className="pointer-events-none absolute inset-0 [background-image:radial-gradient(rgba(255,255,255,0.16)_1px,transparent_1px)] [background-size:22px_22px]" />

        <div className="relative flex items-center gap-2.5">
          <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-white/15 text-base font-black text-white backdrop-blur-sm">
            P
          </span>
          <span className="text-lg font-extrabold tracking-tight text-white">PrepPilot</span>
        </div>

        <div className="relative max-w-md">
          <h2 className="text-3xl font-extrabold leading-tight tracking-tight text-white">
            Walk into your next interview ready.
          </h2>
          <p className="mt-3 text-sm leading-relaxed text-white/80">
            Create a topic, learn it with an AI tutor, then stress-test yourself before the real thing.
          </p>

          <div className="mt-10 flex flex-col gap-5">
            {FEATURES.map(({ icon: Icon, label, desc }) => (
              <div key={label} className="flex items-start gap-3">
                <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-white/15 text-white backdrop-blur-sm">
                  <Icon size={17} />
                </span>
                <div>
                  <p className="text-sm font-bold text-white">{label}</p>
                  <p className="text-xs text-white/70">{desc}</p>
                </div>
              </div>
            ))}
          </div>
        </div>

        <p className="relative text-xs text-white/60">© {new Date().getFullYear()} PrepPilot</p>
      </div>

      <div className="flex w-full flex-1 items-center justify-center px-4 py-12 sm:px-6">
        <div className="w-full max-w-sm">
          <div className="mb-8 flex items-center gap-2.5 lg:hidden">
            <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-gradient-to-br from-primary to-accent text-base font-black text-white">
              P
            </span>
            <span className="text-lg font-extrabold tracking-tight text-fg">PrepPilot</span>
          </div>

          <h1 className="text-2xl font-extrabold tracking-tight text-fg">{title}</h1>
          {subtitle && <p className="mt-1.5 text-sm text-muted">{subtitle}</p>}

          <div className="mt-7">{children}</div>

          {footer && <div className="mt-6 text-sm text-muted">{footer}</div>}
        </div>
      </div>
    </div>
  )
}
