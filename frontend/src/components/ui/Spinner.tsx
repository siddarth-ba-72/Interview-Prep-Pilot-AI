import { Loader2 } from 'lucide-react'

export default function Spinner({ size = 16, className = '' }: { size?: number; className?: string }) {
  return <Loader2 size={size} aria-hidden className={`shrink-0 animate-spin text-graphite motion-reduce:animate-none ${className}`} />
}
