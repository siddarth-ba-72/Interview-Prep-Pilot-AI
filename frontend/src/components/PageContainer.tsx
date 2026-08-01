import type { ReactNode } from 'react'

export default function PageContainer({
  children,
  className = '',
  maxWidth = 'max-w-[1400px]',
}: {
  children: ReactNode
  className?: string
  maxWidth?: string
}) {
  return (
    <div className={`mx-auto w-full ${maxWidth} px-4 py-8 sm:px-6 lg:px-8 ${className}`}>
      {children}
    </div>
  )
}
