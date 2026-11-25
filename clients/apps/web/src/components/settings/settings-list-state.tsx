import type { UseQueryResult } from '@tanstack/react-query'

import { Spinner } from '@/components/ui/spinner'
import { getErrorMessage } from '@/lib/api/errors'

/** What an empty settings list says: loading, why it failed, or that it's empty. */
export function SettingsListState({
  query,
  empty,
}: {
  query: Pick<UseQueryResult, 'isPending' | 'isError' | 'error'>
  empty: string
}) {
  if (query.isPending) {
    return (
      <span className="inline-flex items-center gap-2">
        <Spinner />
        Loading
      </span>
    )
  }
  if (query.isError) {
    return <span>{getErrorMessage(query.error)}</span>
  }
  return <span>{empty}</span>
}
