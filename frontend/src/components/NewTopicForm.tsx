import { FormEvent, useRef, useState } from 'react'
import { Plus, Sparkles } from 'lucide-react'

interface NewTopicFormProps {
  onCreate: (name: string) => Promise<void>
  isSubmitting: boolean
  error: string | null
  /** Topic ideas shown as chips; clicking one fills the input. */
  suggestions?: string[]
}

export default function NewTopicForm({ onCreate, isSubmitting, error, suggestions = [] }: NewTopicFormProps) {
  const disabled = isSubmitting
  const inputRef = useRef<HTMLInputElement>(null)

  const [name, setName] = useState('')

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    if (!name.trim()) return
    await onCreate(name.trim())
    setName('')
  }

  return (
    <div>
      <label htmlFor="new-topic" className="mb-2 block text-sm font-bold text-fg">
        What do you want to master next?
      </label>
      <form
        onSubmit={handleSubmit}
        className="flex items-center gap-2 rounded-2xl border border-border bg-surface p-2 pl-4 shadow-sm transition-all focus-within:border-primary/50 focus-within:shadow-lg focus-within:shadow-primary/15 focus-within:ring-4 focus-within:ring-primary/10"
      >
        <Sparkles size={16} className="shrink-0 text-primary" aria-hidden />
        <input
          ref={inputRef}
          id="new-topic"
          type="text"
          placeholder="e.g. Spring Boot, Python, DevOps"
          value={name}
          onChange={(e) => setName(e.target.value)}
          disabled={disabled}
          className="min-w-0 flex-1 bg-transparent text-sm text-fg outline-none placeholder:text-muted"
        />
        <button
          type="submit"
          disabled={disabled || !name.trim()}
          className="group flex h-10 shrink-0 items-center gap-1.5 rounded-xl bg-gradient-to-r from-primary to-accent px-4 text-sm font-bold text-primary-fg shadow-md shadow-primary/30 transition-all hover:brightness-110 active:scale-95 disabled:cursor-not-allowed disabled:opacity-50 disabled:shadow-none"
        >
          <Plus size={16} className="transition-transform group-enabled:group-hover:rotate-90" />
          <span className="hidden sm:inline">{isSubmitting ? 'Adding...' : 'Add Topic'}</span>
        </button>
      </form>
      {suggestions.length > 0 && !disabled && (
        <div className="mt-3 flex flex-wrap items-center gap-2">
          <span className="text-xs font-semibold text-muted">Try:</span>
          {suggestions.map((suggestion, i) => (
            <button
              key={suggestion}
              type="button"
              onClick={() => {
                setName(suggestion)
                inputRef.current?.focus()
              }}
              style={{ animationDelay: `${150 + i * 60}ms` }}
              className="animate-rise-in rounded-full border border-border bg-surface/80 px-3 py-1 text-xs font-semibold text-fg transition-all hover:-translate-y-0.5 hover:border-primary/40 hover:bg-primary-subtle hover:text-primary"
            >
              {suggestion}
            </button>
          ))}
        </div>
      )}
      {error && <p className="mt-2 text-sm font-medium text-danger">{error}</p>}
    </div>
  )
}
