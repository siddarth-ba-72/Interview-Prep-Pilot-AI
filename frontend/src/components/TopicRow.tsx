import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { Trash2 } from 'lucide-react'
import type { Topic } from '../api/topics'
import { Button } from './ui/Button'
import ScoreBar from './ui/ScoreBar'

export const TEST_MAX = 60
export const TEST_PASS = 36

/**
 * One topic as a row of the list: its name, its average against the pass mark, and the three modes.
 * The row element is the heading's direct parent; the end-to-end tests find a topic's controls that way.
 */
export default function TopicRow({
  topic,
  onDelete,
  isDeleting,
}: {
  topic: Topic
  onDelete: (topicId: string) => void
  isDeleting: boolean
}) {
  const navigate = useNavigate()
  const [confirming, setConfirming] = useState(false)
  const avg = topic.avgScore ?? null
  const tests = topic.testCount ?? 0
  const base = `/topics/${topic.id}`

  return (
    <li
      className={`grid items-center gap-x-6 gap-y-0.5 px-5 py-4 transition-opacity [grid-template-areas:'name''meta''score''actions'] md:grid-cols-[minmax(0,1fr)_200px_auto] md:[grid-template-areas:'name_score_actions''meta_score_actions'] ${
        isDeleting ? 'pointer-events-none opacity-40' : ''
      }`}
    >
      <h3 className="type-section truncate [grid-area:name] md:self-end" title={`${topic.name}, added ${new Date(topic.createdAt).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}`}>
        <Link to={`${base}/learn`} className="no-underline hover:underline">
          {topic.name}
        </Link>
      </h3>

      <p className="type-meta flex flex-wrap items-center gap-x-2 [grid-area:meta] md:self-start">
        <button type="button" onClick={() => navigate(`${base}/tests`)} className="text-graphite underline-offset-4 hover:text-ink hover:underline">
          Test history
        </button>
        <span aria-hidden>·</span>
        <button
          type="button"
          onClick={() => navigate(`${base}/interviews/history`)}
          className="text-graphite underline-offset-4 hover:text-ink hover:underline"
        >
          Interview history
        </button>
      </p>

      <div className="mt-3 [grid-area:score] md:mt-0" data-clarity-mask="True">
        <p className="figures flex items-baseline gap-1.5 text-sm">
          {avg !== null ? (
            <>
              <span className="font-semibold text-ink">{avg.toFixed(1)}</span>
              <span className="text-graphite">/ {TEST_MAX}</span>
              <span className="ml-auto text-xs text-pencil">
                {tests} {tests === 1 ? 'test' : 'tests'}
              </span>
            </>
          ) : (
            <span className="text-graphite">No test taken yet</span>
          )}
        </p>
        <ScoreBar score={avg ?? 0} max={TEST_MAX} pass={TEST_PASS} className="mt-2" />
      </div>

      <div className="mt-3 flex flex-wrap items-center gap-1.5 [grid-area:actions] md:mt-0">
        <Button size="sm" onClick={() => navigate(`${base}/learn`)}>
          Learn
        </Button>
        <Button size="sm" onClick={() => navigate(`${base}/test`)}>
          Test
        </Button>
        <Button size="sm" onClick={() => navigate(`${base}/interviews`)}>
          Mock interview
        </Button>
        {confirming ? (
          <span className="ml-1 inline-flex items-center gap-1">
            <Button
              size="sm"
              variant="danger"
              autoFocus
              onClick={() => {
                setConfirming(false)
                onDelete(topic.id)
              }}
            >
              Confirm
            </Button>
            <Button size="sm" variant="quiet" onClick={() => setConfirming(false)}>
              Keep
            </Button>
          </span>
        ) : (
          <Button
            size="sm"
            variant="quiet"
            onClick={() => setConfirming(true)}
            aria-label={`Delete ${topic.name}`}
            title={`Delete ${topic.name}`}
            className="w-8 px-0 hover:text-redpen"
          >
            <Trash2 size={15} />
          </Button>
        )}
      </div>
    </li>
  )
}
