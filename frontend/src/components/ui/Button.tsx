import { forwardRef, type ButtonHTMLAttributes } from 'react'

export type ButtonVariant = 'primary' | 'secondary' | 'ghost' | 'quiet' | 'danger'
export type ButtonSize = 'sm' | 'md' | 'lg'

const BASE =
  'inline-flex shrink-0 items-center justify-center gap-2 whitespace-nowrap rounded-md font-medium no-underline ' +
  'transition-[background-color,color,border-color,transform] duration-150 ease-out active:scale-[0.97] ' +
  'disabled:pointer-events-none disabled:opacity-50 hover:no-underline'

const VARIANTS: Record<ButtonVariant, string> = {
  /** One per screen: the job the screen exists for. Ink, never a brand colour. */
  primary: 'bg-action text-action-ink hover:bg-action-hover',
  secondary: 'border border-edge bg-sheet text-ink hover:bg-wash',
  ghost: 'text-ink hover:bg-wash',
  /** Utility actions in the chrome: grey until hovered. */
  quiet: 'text-graphite hover:bg-wash hover:text-ink',
  /** Destructive confirmation: the red pen, filled. */
  danger: 'bg-redpen text-white hover:opacity-90',
}

const SIZES: Record<ButtonSize, string> = {
  sm: 'h-8 px-2.5 text-[13px]',
  md: 'h-9 px-3.5 text-sm',
  lg: 'h-10 px-4 text-sm',
}

/** Class names for anything that should look like a button, including router links. */
export function buttonClass({
  variant = 'secondary',
  size = 'md',
  className = '',
}: { variant?: ButtonVariant; size?: ButtonSize; className?: string } = {}): string {
  return `${BASE} ${VARIANTS[variant]} ${SIZES[size]} ${className}`
}

type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & { variant?: ButtonVariant; size?: ButtonSize }

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(function Button(
  { variant = 'secondary', size = 'md', className = '', type = 'button', ...props },
  ref
) {
  return <button ref={ref} type={type} className={buttonClass({ variant, size, className })} {...props} />
})
