'use client'

import { House } from 'lucide-react'
import { useState } from 'react'

import { ListHeading } from '@/components/list-heading'
import { ListRow, RowMark, StatusMeta } from '@/components/list-row'
import { SettingsListState } from '@/components/settings/settings-list-state'
import { useChecklistProperties } from '@/hooks/checklists'
import { counted } from '@/lib/format'
import type { ChecklistProperty } from '@/lib/api/types'
import { describeWatchers } from '@/lib/checklists'

import { ChecklistRecipientsDialog } from './checklist-recipients-dialog'

/** One row per property: who hears about its checklists, or nobody. */
export function ChecklistProperties() {
  const properties = useChecklistProperties()
  const [editing, setEditing] = useState<ChecklistProperty | null>(null)
  const items = properties.data ?? []

  if (items.length === 0) {
    return (
      <p className="py-10 text-center text-sm text-muted-foreground">
        <SettingsListState
          query={properties}
          empty="No properties yet. Add one, then choose who hears about it."
        />
      </p>
    )
  }

  return (
    <>
      <ul className="flex flex-col">
        <ListHeading>{counted(items.length, 'property', 'properties')}</ListHeading>
        {items.map((watchers) => (
          <WatchersRow
            key={watchers.property_id}
            watchers={watchers}
            onEdit={() => setEditing(watchers)}
          />
        ))}
      </ul>

      {editing && (
        <ChecklistRecipientsDialog
          key={editing.property_id}
          watchers={editing}
          open
          onOpenChange={(open) => !open && setEditing(null)}
        />
      )}
    </>
  )
}

function WatchersRow({
  watchers,
  onEdit,
}: {
  watchers: ChecklistProperty
  onEdit: () => void
}) {
  const summary = describeWatchers(watchers)
  const on = watchers.recipients.length > 0

  return (
    <ListRow
      onSelect={onEdit}
      label={`${watchers.property_name}, ${summary}`}
      mark={
        <RowMark className="bg-sky-100 dark:bg-sky-500/20">
          <House className="size-5 text-sky-900 dark:text-sky-100" aria-hidden />
        </RowMark>
      }
      title={watchers.property_name}
      meta={<StatusMeta tone={on ? 'on' : 'off'}>{summary}</StatusMeta>}
    />
  )
}
