import { listAdminFeedback } from '../../api/admin'

export const FEEDBACK_PAGE_SIZE = 20

/** A page of feedback. The admin tabs read page 0 for the count, so the Feedback tab opens already loaded. */
export function feedbackPageQuery(page: number) {
  return {
    queryKey: ['admin', 'feedback', page],
    queryFn: () => listAdminFeedback({ page, size: FEEDBACK_PAGE_SIZE }),
  }
}
