'use client'

import { useState } from 'react'

import { FieldRow, FieldRows, RowInput } from '@/components/dialog-fields'
import { FormDialog } from '@/components/form-dialog'
import { useSetChecklistItem } from '@/hooks/checklists'
import { getErrorMessage } from '@/lib/api/errors'
import type { ChecklistItem } from '@/lib/api/types'

/** What somebody saw at one item: a leak, a missing towel. Empty removes it. */
export function NoteDialog({
  checklistId,
  item,
  open,
  onOpenChange,
}: {
  checklistId: string
  item: ChecklistItem
  open: boolean
  onOpenChange: (open: boolean) => void
}) {
  const setItem = useSetChecklistItem(checklistId)
  const [note, setNote] = useState(item.note ?? '')
  const [error, setError] = useState<string>()

  const submit = async () => {
    try {
      await setItem.mutateAsync({ itemId: item.id, body: { note: note.trim() || null } })
      onOpenChange(false)
    } catch (failure) {
      setError(getErrorMessage(failure))
    }
  }

  return (
    <FormDialog
      title={item.description}
      open={open}
      onOpenChange={onOpenChange}
      onSubmit={() => void submit()}
      submitLabel="Save note"
      pending={setItem.isPending}
      error={error}
    >
      <FieldRows>
        <FieldRow label="Note">
          <RowInput
            value={note}
            onChange={(event) => setNote(event.target.value)}
            placeholder="What you saw"
            maxLength={2000}
            autoFocus
          />
        </FieldRow>
      </FieldRows>
    </FormDialog>
  )
}
