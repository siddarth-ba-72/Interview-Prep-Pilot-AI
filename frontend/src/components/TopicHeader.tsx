import type { ReactNode } from 'react'
import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { listTopics } from '../api/topics'
import { WIDTH } from './PageContainer'

export type TopicTab = 'learn' | 'test' | 'interview' | 'history'

const TABS: Array<{ key: TopicTab; label: string; path: string }> = [
  { key: 'learn', label: 'Learn', path: 'learn' },
  { key: 'test', label: 'Test', path: 'test' },
  { key: 'interview', label: 'Mock interview', path: 'interviews' },
  { key: 'history', label: 'History', path: 'tests' },
]

/** The topic's name, from the cached topic list every topic screen shares. */
export function useTopicName(topicId: string | undefined): string | undefined {
  const topicsQuery = useQuery({ queryKey: ['topics'], queryFn: listTopics, staleTime: 60_000 })
  return topicsQuery.data?.find((topic) => topic.id === topicId)?.name
}

/**
 * The head of every screen inside a topic: the way back to all topics, the topic as the screen's
 * title, and the study loop as tabs (Learn, Test, Mock interview, then the history of both).
 */
export default function TopicHeader({
  topicId,
  active,
  actions,
}: {
  topicId: string
  active: TopicTab
  actions?: ReactNode
}) {
  const topicName = useTopicName(topicId)

  return (
    <div className="border-b border-line">
      <div className={`mx-auto w-full ${WIDTH.topic} px-4 sm:px-6 lg:px-8`}>
        <div className="flex items-end justify-between gap-4 pt-5">
          <div className="min-w-0">
            <Link to="/dashboard" className="type-meta text-graphite no-underline hover:text-ink hover:underline">
              Topics
            </Link>
            <h1 className="type-title mt-0.5 truncate" title={topicName}>
              {topicName ?? <span className="inline-block h-6 w-40 rounded bg-press align-middle" aria-label="Loading topic" />}
            </h1>
          </div>
          {actions && <div className="flex shrink-0 items-center gap-2 pb-0.5">{actions}</div>}
        </div>

        <nav aria-label="Topic" className="-mb-px mt-3 flex gap-5 overflow-x-auto [scrollbar-width:none]">
          {TABS.map((tab) => {
            const current = tab.key === active
            return (
              <Link
                key={tab.key}
                to={`/topics/${topicId}/${tab.path}`}
                aria-current={current ? 'page' : undefined}
                className={`shrink-0 border-b-2 pb-2.5 pt-1 text-sm no-underline transition-colors duration-150 hover:no-underline ${
                  current ? 'border-ink font-medium text-ink' : 'border-transparent text-graphite hover:text-ink'
                }`}
              >
                {tab.label}
              </Link>
            )
          })}
        </nav>
      </div>
    </div>
  )
}
