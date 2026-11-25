'use client'

import { FieldRow, Panel } from '@/components/dialog-fields'
import { Checkbox } from '@/components/ui/checkbox'
import type { Property } from '@/lib/api/types'

/** The properties a homeowner sees, ticked in a tinted panel. */
export function PropertyChecklist({
  properties,
  selected,
  onChange,
  disabled,
}: {
  properties: Property[]
  selected: string[]
  onChange: (ids: string[]) => void
  disabled: boolean
}) {
  const choices = properties.filter(
    (property) => !property.is_archived || selected.includes(property.id),
  )
  const toggle = (id: string) =>
    onChange(
      selected.includes(id)
        ? selected.filter((value) => value !== id)
        : [...selected, id],
    )

  return (
    <Panel className="max-h-56 overflow-y-auto">
      {choices.length === 0 && (
        <p className="py-2 text-sm text-muted-foreground">Add a property first.</p>
      )}
      {choices.map((property) => (
        <FieldRow key={property.id} label={property.name}>
          <Checkbox
            aria-label={property.name}
            checked={selected.includes(property.id)}
            onCheckedChange={() => toggle(property.id)}
            disabled={disabled}
          />
        </FieldRow>
      ))}
    </Panel>
  )
}
