import { FormEvent, useState } from 'react'
import { Plus } from 'lucide-react'

interface NewTopicFormProps {
  onCreate: (name: string) => Promise<void>
  isSubmitting: boolean
  error: string | null
  /** Set when the user may not add a topic right now; disables the form and explains why. */
  disabledReason?: string | null
}

export default function NewTopicForm({ onCreate, isSubmitting, error, disabledReason }: NewTopicFormProps) {
  const disabled = isSubmitting || Boolean(disabledReason)

  const [name, setName] = useState('')

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    if (!name.trim()) return
    await onCreate(name.trim())
    setName('')
  }

  return (
    <div>
      <form
        onSubmit={handleSubmit}
        className="flex items-center gap-2 rounded-2xl border border-border bg-surface p-2 pl-4 shadow-sm"
      >
        <input
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
          className="flex h-10 shrink-0 items-center gap-1.5 rounded-xl bg-primary px-4 text-sm font-bold text-primary-fg transition-colors hover:bg-primary-hover disabled:cursor-not-allowed disabled:opacity-50"
        >
          <Plus size={16} />
          <span className="hidden sm:inline">{isSubmitting ? 'Adding...' : 'Add Topic'}</span>
        </button>
      </form>
      {disabledReason && <p className="mt-2 text-sm text-muted">{disabledReason}</p>}
      {error && !disabledReason && <p className="mt-2 text-sm font-medium text-danger">{error}</p>}
    </div>
  )
}
