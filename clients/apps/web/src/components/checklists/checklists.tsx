'use client'

import { ClipboardCheck, Plus } from 'lucide-react'
import { usePathname, useRouter, useSearchParams } from 'next/navigation'
import { useState } from 'react'

import { ListHeading } from '@/components/list-heading'
import { ListRow, RowMark, StatusMeta } from '@/components/list-row'
import { PageAction, PageHeader } from '@/components/page-header'
import { useCompany, usePermissions } from '@/components/session-context'
import { SettingsListState } from '@/components/settings/settings-list-state'
import { TabPills } from '@/components/tab-pills'
import { useChecklists } from '@/hooks/checklists'
import { useProperties } from '@/hooks/ledger'
import type { Checklist } from '@/lib/api/types'
import { checklistTabs } from '@/lib/checklist-tabs'
import { describeChecklist, describeProgress, splitByDay } from '@/lib/checklists'
import { formatDayHeading, todayIn } from '@/lib/format'

import { ChecklistProperties } from './checklist-properties'
import { StartChecklistDialog } from './start-checklist-dialog'

/**
 * Every walk of every property, the ones under way pinned above the rest.
 *
 * The number at the end of a row is the point of it: a finished walk with items
 * unticked is the one somebody needs to look at.
 */
export function Checklists() {
  const router = useRouter()
  const pathname = usePathname()
  const searchParams = useSearchParams()
  const { manages } = usePermissions()
  // A homeowner is only shown the walks; who hears about them is not theirs.
  const tab = manages ? checklistTabs.parse(searchParams) : 'history'
  const company = useCompany()
  const timezone = company.data?.timezone ?? 'America/Mazatlan'
  const checklists = useChecklists()
  const properties = useProperties()
  const [starting, setStarting] = useState(false)
  const names = new Map((properties.data ?? []).map((one) => [one.id, one.name]))
  const { open, days } = splitByDay(checklists.data ?? [], timezone)
  const today = todayIn(timezone)

  return (
    <>
      <PageHeader
        title="Checklists"
        actions={
          manages ? (
            <PageAction
              label="Start checklist"
              icon={<Plus className="size-4" />}
              onClick={() => setStarting(true)}
            />
          ) : undefined
        }
      />

      {manages && (
        <TabPills
          label="Checklists"
          tabs={checklistTabs.tabs}
          current={tab}
          labels={checklistTabs.labels}
          onSelect={(chosen) => {
            const search = checklistTabs.search(chosen)
            router.replace(search ? `${pathname}?${search}` : pathname, { scroll: false })
          }}
        />
      )}

      {tab === 'properties' ? (
        <ChecklistProperties />
      ) : (checklists.data ?? []).length === 0 ? (
        <p className="py-10 text-center text-sm text-muted-foreground">
          <SettingsListState
            query={checklists}
            empty={
              manages
                ? 'No checklists yet. Start one and walk a property with it.'
                : 'No checklists of your properties yet.'
            }
          />
        </p>
      ) : (
        <div className="flex flex-col gap-8">
          {open.length > 0 && (
            <section aria-label="In progress">
              <ListHeading>In progress</ListHeading>
              <ul className="flex flex-col">
                {open.map((one) => (
                  <ChecklistRow
                    key={one.id}
                    checklist={one}
                    name={names.get(one.property_id)}
                  />
                ))}
              </ul>
            </section>
          )}
          {days.map((day) => (
            <section key={day.date} aria-label={formatDayHeading(day.date, today)}>
              <ListHeading>{formatDayHeading(day.date, today)}</ListHeading>
              <ul className="flex flex-col">
                {day.checklists.map((one) => (
                  <ChecklistRow
                    key={one.id}
                    checklist={one}
                    name={names.get(one.property_id)}
                  />
                ))}
              </ul>
            </section>
          ))}
        </div>
      )}

      {starting && <StartChecklistDialog open onOpenChange={setStarting} />}
    </>
  )
}

function ChecklistRow({ checklist, name }: { checklist: Checklist; name?: string }) {
  const router = useRouter()
  const summary = describeChecklist(checklist)
  const title = name ?? 'Property'

  return (
    <ListRow
      onSelect={() => router.push(`/checklists/${checklist.id}`)}
      label={`${title}, ${summary}`}
      mark={
        <RowMark className="bg-violet-100 dark:bg-violet-500/20">
          <ClipboardCheck
            className="size-5 text-violet-900 dark:text-violet-100"
            aria-hidden
          />
        </RowMark>
      }
      title={title}
      meta={
        <StatusMeta tone={checklist.completed_at === null ? 'busy' : 'on'}>
          {summary}
        </StatusMeta>
      }
      trailing={
        <span className="shrink-0 text-sm text-muted-foreground tabular-nums">
          {describeProgress(checklist)}
        </span>
      }
    />
  )
}
