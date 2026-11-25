'use client'

import { useState } from 'react'

import { FieldRow, Panel } from '@/components/dialog-fields'
import { FormDialog } from '@/components/form-dialog'
import { Checkbox } from '@/components/ui/checkbox'
import type { GuestExpense } from '@/lib/api/types'
import { formatDate, formatMoney, sentence } from '@/lib/format'

/**
 * A property's unbilled guest expenses, every one ticked: billing a stay is
 * usually billing all of it, and unticking the odd one is quicker than ticking
 * the rest.
 */
export function GuestExpensePicker({
  expenses,
  currency,
  open,
  onOpenChange,
  onPick,
}: {
  expenses: GuestExpense[]
  currency: string
  open: boolean
  onOpenChange: (open: boolean) => void
  onPick: (picked: GuestExpense[]) => void
}) {
  const [chosen, setChosen] = useState(() => new Set(expenses.map((one) => one.id)))
  const picked = expenses.filter((one) => chosen.has(one.id))

  const toggle = (id: string) =>
    setChosen((current) => {
      const next = new Set(current)
      if (!next.delete(id)) next.add(id)
      return next
    })

  return (
    <FormDialog
      title="Bill guest expenses"
      open={open}
      onOpenChange={onOpenChange}
      onSubmit={() => {
        onPick(picked)
        onOpenChange(false)
      }}
      submitLabel={picked.length === 1 ? 'Add 1 line' : `Add ${picked.length} lines`}
      disabled={picked.length === 0}
    >
      <Panel className="max-h-80 overflow-y-auto">
        {expenses.map((expense) => {
          const name = sentence(expense.description || expense.concept)
          return (
            <FieldRow key={expense.id} label={name}>
              <span className="flex items-center gap-3">
                <span className="text-sm whitespace-nowrap text-muted-foreground tabular-nums">
                  {formatDate(expense.date)} · {formatMoney(expense.amount, currency)}
                </span>
                <Checkbox
                  aria-label={name}
                  checked={chosen.has(expense.id)}
                  onCheckedChange={() => toggle(expense.id)}
                />
              </span>
            </FieldRow>
          )
        })}
      </Panel>
    </FormDialog>
  )
}
