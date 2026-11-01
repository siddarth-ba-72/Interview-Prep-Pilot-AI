import { FormEvent, useRef, useState } from 'react'
import { Plus } from 'lucide-react'
import { Button } from './ui/Button'
import { inputClass } from './ui/field'

interface NewTopicFormProps {
  onCreate: (name: string) => Promise<void>
  isSubmitting: boolean
  error: string | null
  /** Topic ideas shown under the field; picking one fills it. */
  suggestions?: string[]
}

export default function NewTopicForm({ onCreate, isSubmitting, error, suggestions = [] }: NewTopicFormProps) {
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
      <form onSubmit={handleSubmit} className="flex gap-2">
        <label htmlFor="new-topic" className="sr-only">
          New topic
        </label>
        <input
          ref={inputRef}
          id="new-topic"
          type="text"
          autoComplete="off"
          placeholder="e.g. Spring Boot, Python, DevOps"
          value={name}
          onChange={(e) => setName(e.target.value)}
          disabled={isSubmitting}
          aria-describedby={error ? 'new-topic-error' : undefined}
          className={inputClass}
        />
        <Button type="submit" variant="primary" size="lg" disabled={isSubmitting || !name.trim()}>
          <Plus size={16} aria-hidden />
          <span className="sm:hidden">{isSubmitting ? 'Adding…' : 'Add'}</span>
          <span className="hidden sm:inline">{isSubmitting ? 'Adding…' : 'Add topic'}</span>
        </Button>
      </form>

      {error && (
        <p id="new-topic-error" role="alert" className="mt-2 text-sm text-redpen">
          {error}
        </p>
      )}

      {suggestions.length > 0 && !isSubmitting && (
        <p className="mt-2.5 flex flex-wrap items-center gap-x-2.5 gap-y-1 text-[13px] text-graphite">
          <span>Try</span>
          {suggestions.map((suggestion, i) => (
            <span key={suggestion} className="inline-flex items-center">
              <button
                type="button"
                onClick={() => {
                  setName(suggestion)
                  inputRef.current?.focus()
                }}
                className="rounded-sm py-0.5 text-ink underline decoration-edge underline-offset-4 transition-colors hover:decoration-ink"
              >
                {suggestion}
              </button>
              {i < suggestions.length - 1 && <span aria-hidden>,</span>}
            </span>
          ))}
        </p>
      )}
    </div>
  )
}
