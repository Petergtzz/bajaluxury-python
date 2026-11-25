'use client'

import { Download, House } from 'lucide-react'

import { ListHeading } from '@/components/list-heading'
import { ListRow, RowMark, StatusMeta } from '@/components/list-row'
import { SettingsListState } from '@/components/settings/settings-list-state'
import { statementURL, useSentStatements } from '@/hooks/reports'
import type { SentStatement } from '@/lib/api/types'
import { useCompany } from '@/components/session-context'
import { formatMomentDay } from '@/lib/format'
import { describeSent, monthName } from '@/lib/reports'
import { groupConsecutive } from '@/lib/format'

/**
 * What has actually gone out, month by month.
 *
 * The record, rather than the setup: every property's statement for a month
 * under that month's heading, so "did August go?" is one glance instead of a
 * property-by-property hunt.
 */
export function StatementHistory() {
  const statements = useSentStatements()
  const sends = statements.data ?? []

  if (sends.length === 0) {
    return (
      <div className="py-10 text-center text-sm text-muted-foreground">
        <SettingsListState
          query={statements}
          empty="Nothing has been sent yet. A statement shows up here on the day its property reports."
        />
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-9">
      {groupConsecutive(sends, (send) => send.month).map((month) => (
        <section key={month.key} aria-label={monthName(month.key)}>
          <ListHeading>{monthName(month.key)}</ListHeading>
          <ul className="flex flex-col">
            {month.items.map((send) => (
              <StatementRow key={send.id} send={send} />
            ))}
          </ul>
        </section>
      ))}
    </div>
  )
}

function StatementRow({ send }: { send: SentStatement }) {
  const timezone = useCompany().data?.timezone ?? 'America/Mazatlan'
  // The file as it was sent, kept by the API; it opens beside the page.
  const download = () => {
    window.open(statementURL(send.id), '_blank', 'noopener,noreferrer')
  }

  return (
    <ListRow
      label={`${send.property_name}, ${describeSent(send)}`}
      mark={
        <RowMark className="bg-sky-100 dark:bg-sky-500/20">
          <House className="size-5 text-sky-900 dark:text-sky-100" aria-hidden />
        </RowMark>
      }
      title={send.property_name}
      meta={
        <StatusMeta tone={send.status === 'sent' ? 'on' : 'off'}>
          {describeSent(send)}
        </StatusMeta>
      }
      trailing={
        <span className="flex shrink-0 items-center gap-3">
          <span className="text-sm text-muted-foreground">
            {send.sent_at
              ? `Sent ${formatMomentDay(send.sent_at, timezone)}`
              : 'Not sent'}
          </span>
          {send.has_statement && (
            <button
              type="button"
              onClick={download}
              aria-label={`Download ${send.property_name}, ${monthName(send.month)}`}
              className="flex size-9 items-center justify-center rounded-lg text-muted-foreground transition-colors hover:bg-neutral-200/70 hover:text-neutral-900 focus-visible:ring-[3px] focus-visible:ring-ring/50 focus-visible:outline-none dark:hover:bg-neutral-700 dark:hover:text-neutral-100"
            >
              <Download className="size-[18px]" />
            </button>
          )}
        </span>
      }
    />
  )
}
