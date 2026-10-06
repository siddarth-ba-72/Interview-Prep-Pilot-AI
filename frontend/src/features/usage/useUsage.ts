import { useQuery } from '@tanstack/react-query'
import { USAGE_QUERY_KEY, getUsage } from '../../api/usage'

/** The signed-in user's limits and what is left of them. Callers invalidate
 * USAGE_QUERY_KEY after anything that spends a use. */
export function useUsage() {
  return useQuery({ queryKey: USAGE_QUERY_KEY, queryFn: getUsage })
}
