'use client'

import { House, Send } from 'lucide-react'
import { usePathname, useRouter, useSearchParams } from 'next/navigation'
import { useState } from 'react'

import { ListRow, RowMark, StatusMeta } from '@/components/list-row'
import { useCompany, usePermissions } from '@/components/session-context'
import { PageAction, PageHeader } from '@/components/page-header'
import { ListHeading } from '@/components/list-heading'
import { SettingsListState } from '@/components/settings/settings-list-state'
import { TabPills } from '@/components/tab-pills'
import { useFailedStatementCount, useReports } from '@/hooks/reports'
import type { Report } from '@/lib/api/types'
import { counted } from '@/lib/format'
import { describeRecipients, describeSchedule } from '@/lib/reports'
import { reportTabs } from '@/lib/report-tabs'

import { FailedStatementsNotice } from './failed-statements-notice'
import { ReportDialog } from './report-dialog'
import { SendReportDialog } from './send-report-dialog'
import { StatementHistory } from './statement-history'

/**
 * Reports in two halves: what each property sends, and what has gone out.
 *
 * Properties is the setup - one row per property, saying who its statement goes
 * to and when. History is the record. A month that didn't go is announced once,
 * above both, rather than dressed into every row that isn't about it.
 *
 * A homeowner gets the record alone: the statements of their own properties,
 * each with the file that was sent. Setting a report up is not theirs, and
 * neither is a month that failed to reach somebody, which somebody else has to
 * put right.
 */
export function Reports() {
  const router = useRouter()
  const pathname = usePathname()
  const searchParams = useSearchParams()
  const { manages } = usePermissions()
  const company = useCompany()
  const tab = manages ? reportTabs.parse(searchParams) : 'history'
  const reports = useReports(manages)
  const failed = useFailedStatementCount(manages)
  const [editing, setEditing] = useState<Report | null>(null)
  const [sending, setSending] = useState(false)
  const items = reports.data ?? []

  return (
    <>
      <PageHeader
        title="Reports"
        actions={
          manages ? (
            <PageAction
              label="Send report"
              icon={<Send className="size-4" />}
              onClick={() => setSending(true)}
            />
          ) : undefined
        }
      />

      {manages && (
        <TabPills
          label="Reports"
          tabs={reportTabs.tabs}
          current={tab}
          labels={reportTabs.labels}
          counts={{ history: failed.data }}
          onSelect={(chosen) => {
            const search = reportTabs.search(chosen)
            router.replace(search ? `${pathname}?${search}` : pathname, {
              scroll: false,
            })
          }}
        />
      )}

      {manages && <FailedStatementsNotice />}

      {tab === 'history' ? (
        <StatementHistory />
      ) : items.length === 0 ? (
        <div className="py-10 text-center text-sm text-muted-foreground">
          <SettingsListState
            query={reports}
            empty="No properties yet. Add one, then choose who hears about it."
          />
        </div>
      ) : (
        <ul className="flex flex-col">
          <ListHeading>{counted(items.length, 'property', 'properties')}</ListHeading>
          {items.map((report) => (
            <ReportRow
              key={report.property_id}
              report={report}
              onEdit={() => setEditing(report)}
            />
          ))}
        </ul>
      )}

      {sending && (
        <SendReportDialog
          reports={items}
          timezone={company.data?.timezone ?? 'America/Mazatlan'}
          open
          onOpenChange={(open) => !open && setSending(false)}
        />
      )}

      {tab === 'properties' && editing && (
        <ReportDialog
          key={editing.property_id}
          report={editing}
          open
          onOpenChange={(open) => !open && setEditing(null)}
        />
      )}
    </>
  )
}

/** The row's quiet line: who it goes to, and when, or that it goes nowhere. */
const summary = (report: Report) =>
  report.recipients.length === 0
    ? describeRecipients(report)
    : `${describeRecipients(report)} · ${describeSchedule(report)}`

function ReportRow({ report, onEdit }: { report: Report; onEdit: () => void }) {
  const isOn = report.recipients.length > 0

  return (
    <ListRow
      onSelect={onEdit}
      label={`${report.property_name}, ${summary(report)}`}
      mark={
        <RowMark className="bg-sky-100 dark:bg-sky-500/20">
          <House className="size-5 text-sky-900 dark:text-sky-100" aria-hidden />
        </RowMark>
      }
      title={report.property_name}
      meta={<StatusMeta tone={isOn ? 'on' : 'off'}>{summary(report)}</StatusMeta>}
    />
  )
}
