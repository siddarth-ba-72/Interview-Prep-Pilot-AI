import { FormEvent, useState } from 'react'

interface NewTopicFormProps {
  onCreate: (name: string) => Promise<void>
  isSubmitting: boolean
  error: string | null
}

export default function NewTopicForm({ onCreate, isSubmitting, error }: NewTopicFormProps) {
  const [name, setName] = useState('')

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    if (!name.trim()) return
    await onCreate(name.trim())
    setName('')
  }

  return (
    <form className="new-topic-form" onSubmit={handleSubmit}>
      <input
        type="text"
        placeholder="e.g. Spring Boot, Python, DevOps"
        value={name}
        onChange={(e) => setName(e.target.value)}
        disabled={isSubmitting}
      />
      <button type="submit" className="primary-button" disabled={isSubmitting || !name.trim()}>
        {isSubmitting ? 'Adding...' : 'Add Topic'}
      </button>
      {error && <p className="error-text">{error}</p>}
    </form>
  )
}
