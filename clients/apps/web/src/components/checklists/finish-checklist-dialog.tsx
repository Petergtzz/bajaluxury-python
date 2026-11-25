'use client'

import { useRouter } from 'next/navigation'
import { useState } from 'react'
import { toast } from 'sonner'

import { FieldRow, FieldRows, RowInput } from '@/components/dialog-fields'
import { FormDialog } from '@/components/form-dialog'
import { RecipientPicker } from '@/components/recipient-picker'
import { useCompleteChecklist } from '@/hooks/checklists'
import { useHomeownerProperties, useMembers } from '@/hooks/team'
import { getErrorMessage } from '@/lib/api/errors'
import type { Checklist } from '@/lib/api/types'
import { counted } from '@/lib/format'
import { eligibleRecipients, isHomeowner } from '@/lib/reports'

/**
 * Who hears about a finished walk, then it is frozen and its report emailed.
 *
 * The property's owners are ticked to begin with, as they are who it is for.
 * Anybody else - a guest, a cleaner - can be added by address. The company's
 * owners are copied on every report anyway, so ticking them is not needed.
 */
export function FinishChecklistDialog({
  checklist,
  propertyName,
  open,
  onOpenChange,
}: {
  checklist: Checklist
  propertyName: string
  open: boolean
  onOpenChange: (open: boolean) => void
}) {
  const router = useRouter()
  const members = useMembers()
  const everyone = members.data ?? []
  const choices = eligibleRecipients(
    everyone,
    useHomeownerProperties(everyone),
    checklist.property_id,
  )
  const complete = useCompleteChecklist(checklist.id)
  // Who is ticked; until somebody touches the list, the property's owners.
  const [touched, setTouched] = useState<Set<string> | null>(null)
  const chosen = touched ?? new Set(choices.filter(isHomeowner).map((one) => one.user_id))
  const [other, setOther] = useState('')
  const [error, setError] = useState<string>()

  const toggle = (userId: string) => {
    setError(undefined)
    const next = new Set(chosen)
    if (!next.delete(userId)) next.add(userId)
    setTouched(next)
  }

  const submit = async () => {
    const recipients = [
      ...choices.filter((one) => chosen.has(one.user_id)).map((one) => one.email),
      ...(other.trim() ? [other.trim()] : []),
    ]
    if (recipients.length === 0) {
      setError('Tick somebody to send the report to.')
      return
    }
    try {
      await complete.mutateAsync(recipients)
    } catch (failure) {
      setError(getErrorMessage(failure))
      return
    }
    onOpenChange(false)
    toast.success(
      `Checklist finished, sent to ${counted(recipients.length, 'person', 'people')}`,
    )
    router.push('/checklists')
  }

  return (
    <FormDialog
      title="Finish checklist"
      open={open}
      onOpenChange={onOpenChange}
      onSubmit={() => void submit()}
      submitLabel="Finish and send"
      pending={complete.isPending}
      error={error}
    >
      <p className="text-sm text-muted-foreground">
        The {propertyName} report is emailed to the people ticked. It can’t be changed
        after.
      </p>

      <RecipientPicker
        choices={choices}
        chosen={chosen}
        onToggle={toggle}
        loading={members.isPending}
        disabled={complete.isPending}
        addressed={false}
      />

      <FieldRows>
        <FieldRow label="Also to">
          <RowInput
            type="email"
            value={other}
            onChange={(event) => {
              setError(undefined)
              setOther(event.target.value)
            }}
            placeholder="email@example.com"
            disabled={complete.isPending}
          />
        </FieldRow>
      </FieldRows>
    </FormDialog>
  )
}
