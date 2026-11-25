'use client'

import { useRouter } from 'next/navigation'
import { useState } from 'react'

import { FieldRow, FieldRows, RowSelect, SelectItem } from '@/components/dialog-fields'
import { FormDialog } from '@/components/form-dialog'
import { useChecklistTemplates, useStartChecklist } from '@/hooks/checklists'
import { useProperties } from '@/hooks/ledger'
import { getErrorMessage } from '@/lib/api/errors'
import type { ChecklistType } from '@/lib/api/types'
import { CHECKLIST_TYPES, TYPE_NAMES } from '@/lib/checklists'

/** Which property, and which list to walk it with. Then straight to the walk. */
export function StartChecklistDialog({
  open,
  onOpenChange,
}: {
  open: boolean
  onOpenChange: (open: boolean) => void
}) {
  const router = useRouter()
  const start = useStartChecklist()
  const properties = (useProperties().data ?? []).filter(
    (property) => !property.is_archived,
  )
  const templates = useChecklistTemplates().data ?? []
  // A type with nothing on its template would start an empty walk.
  const types = CHECKLIST_TYPES.filter((type) =>
    templates.some((item) => item.type === type),
  )
  const [propertyId, setPropertyId] = useState('')
  const [type, setType] = useState<ChecklistType | ''>('')
  const [error, setError] = useState<string>()

  const submit = async () => {
    if (!propertyId || !type) {
      setError('Pick a property and a checklist.')
      return
    }
    try {
      const checklist = await start.mutateAsync({ property_id: propertyId, type })
      onOpenChange(false)
      router.push(`/checklists/${checklist.id}`)
    } catch (failure) {
      setError(getErrorMessage(failure))
    }
  }

  return (
    <FormDialog
      title="Start checklist"
      open={open}
      onOpenChange={onOpenChange}
      onSubmit={() => void submit()}
      submitLabel="Start walking"
      pending={start.isPending}
      error={error}
    >
      <FieldRows>
        <FieldRow label="Property">
          <RowSelect
            label="Property"
            value={propertyId}
            onValueChange={(value) => {
              setPropertyId(value)
              setError(undefined)
            }}
            placeholder="Select"
            disabled={start.isPending}
          >
            {properties.map((property) => (
              <SelectItem key={property.id} value={property.id}>
                {property.name}
              </SelectItem>
            ))}
          </RowSelect>
        </FieldRow>
        <FieldRow label="Checklist">
          <RowSelect
            label="Checklist"
            value={type}
            onValueChange={(value) => {
              setType(value as ChecklistType)
              setError(undefined)
            }}
            placeholder="Select"
            disabled={start.isPending}
          >
            {types.map((one) => (
              <SelectItem key={one} value={one}>
                {TYPE_NAMES[one]}
              </SelectItem>
            ))}
          </RowSelect>
        </FieldRow>
      </FieldRows>
    </FormDialog>
  )
}
