import type { ReactNode } from 'react'

/** Column widths, so screens of one kind share their left and right edges. */
export const WIDTH = {
  /** Dashboard and admin: the full canvas. */
  wide: 'max-w-[1200px]',
  /** Every screen inside a topic: Learn, Test, Mock interview, History and the reports. */
  topic: 'max-w-4xl',
}

export default function PageContainer({
  children,
  className = '',
  maxWidth = WIDTH.wide,
  mask = false,
}: {
  children: ReactNode
  className?: string
  maxWidth?: string
  /** Hides the contents from Clarity recordings; set it wherever answers, scores, reports or user data show */
  mask?: boolean
}) {
  return (
    <div
      className={`mx-auto w-full ${maxWidth} px-4 py-6 sm:px-6 sm:py-8 lg:px-8 ${className}`}
      data-clarity-mask={mask ? 'True' : undefined}
    >
      {children}
    </div>
  )
}
