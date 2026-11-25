'use client'

import { useSentStatements } from '@/hooks/reports'
import { WarningNotice } from '@/components/warning-notice'
import type { SentStatement } from '@/lib/api/types'
import { counted } from '@/lib/format'
import { monthName } from '@/lib/reports'

/** The properties a month didn't reach, in a sentence: "Colinas 21 and Parque 7". */
const listNames = (sends: SentStatement[]): string => {
  const names = [...new Set(sends.map((send) => send.property_name))]
  const last = names.pop()
  return names.length === 0 ? (last ?? '') : `${names.join(', ')} and ${last}`
}

/**
 * The one place a failure raises its voice.
 *
 * Rows stay quiet and uniform, so something that needs attention would be lost
 * among them. It says which month didn't reach whom, and goes as soon as the
 * statement does.
 */
export function FailedStatementsNotice() {
  const statements = useSentStatements()
  const failed = (statements.data ?? []).filter((send) => send.status === 'failed')
  if (failed.length === 0) {
    return null
  }

  // Newest month first, so the sentence is about the one that just happened.
  const month = failed[0]!.month
  const inMonth = failed.filter((send) => send.month === month)
  const rest = failed.length - inMonth.length

  return (
    <WarningNotice>
      <span className="font-semibold">
        {monthName(month)} didn&apos;t reach {listNames(inMonth)}.
      </span>{' '}
      {inMonth[0]?.error}
      {rest > 0 && ` ${counted(rest, 'earlier month', 'earlier months')} too.`}
    </WarningNotice>
  )
}
