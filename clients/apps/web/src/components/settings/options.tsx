'use client'

import { ClipboardCheck } from 'lucide-react'
import { useState } from 'react'

import { ListRow, RowMark } from '@/components/list-row'
import { useChecklistTemplates } from '@/hooks/checklists'
import type { ChecklistType } from '@/lib/api/types'
import { CHECKLIST_TYPES, TYPE_NAMES } from '@/lib/checklists'
import { describeTemplate } from '@/lib/settings/templates'

import { SettingsPage } from './settings-layout'
import { SettingsListState } from './settings-list-state'
import { TemplateDialog } from './template-dialog'

/**
 * The lists a house is walked with: one for a check-in, one for a check-out,
 * one for the weekly visit. Each row opens its items.
 */
export function Options() {
  const templates = useChecklistTemplates()
  const [editing, setEditing] = useState<{ type: ChecklistType; key: number } | null>(
    null,
  )
  const [open, setOpen] = useState(false)
  const items = (type: ChecklistType) =>
    (templates.data ?? []).filter((item) => item.type === type)

  return (
    <SettingsPage
      title="Options"
      description="The checklists a house is walked with. A walk takes the items as they read when it starts."
    >
      {!templates.data ? (
        <p className="py-10 text-center text-sm text-muted-foreground">
          <SettingsListState query={templates} empty="" />
        </p>
      ) : (
        <ul className="flex flex-col">
          {CHECKLIST_TYPES.map((type) => (
            <ListRow
              key={type}
              onSelect={() => {
                setEditing({ type, key: Date.now() })
                setOpen(true)
              }}
              label={`Edit ${TYPE_NAMES[type]}`}
              mark={
                <RowMark className="bg-violet-100 dark:bg-violet-500/20">
                  <ClipboardCheck
                    className="size-5 text-violet-900 dark:text-violet-100"
                    aria-hidden
                  />
                </RowMark>
              }
              title={TYPE_NAMES[type]}
              meta={<span className="truncate">{describeTemplate(items(type))}</span>}
            />
          ))}
        </ul>
      )}

      {editing && (
        <TemplateDialog
          key={editing.key}
          type={editing.type}
          items={items(editing.type)}
          open={open}
          onOpenChange={setOpen}
        />
      )}
    </SettingsPage>
  )
}
