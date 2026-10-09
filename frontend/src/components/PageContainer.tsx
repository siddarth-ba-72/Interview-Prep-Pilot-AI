import type { ReactNode } from 'react'

export default function PageContainer({
  children,
  className = '',
  maxWidth = 'max-w-[1400px]',
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
      className={`mx-auto w-full ${maxWidth} px-4 py-8 sm:px-6 lg:px-8 ${className}`}
      data-clarity-mask={mask ? 'True' : undefined}
    >
      {children}
    </div>
  )
}
