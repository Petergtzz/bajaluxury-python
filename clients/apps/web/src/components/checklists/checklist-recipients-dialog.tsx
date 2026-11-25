'use client'

import { useState } from 'react'
import { toast } from 'sonner'

import { FormDialog } from '@/components/form-dialog'
import { RecipientPicker } from '@/components/recipient-picker'
import { useSaveChecklistRecipients } from '@/hooks/checklists'
import { useHomeownerProperties, useMembers } from '@/hooks/team'
import { getErrorMessage } from '@/lib/api/errors'
import type { ChecklistProperty } from '@/lib/api/types'
import { addressing, eligibleRecipients } from '@/lib/reports'

/**
 * Who hears about one property's checklists.
 *
 * The same list Reports uses, minus the day: a checklist is sent when a
 * manager finishes walking it, so there is nothing to schedule. Saving with
 * nobody ticked is how it is turned off; the company's owners hear anyway.
 */
export function ChecklistRecipientsDialog({
  watchers,
  open,
  onOpenChange,
}: {
  watchers: ChecklistProperty
  open: boolean
  onOpenChange: (open: boolean) => void
}) {
  const members = useMembers()
  const everyone = members.data ?? []
  const homeownerProperties = useHomeownerProperties(everyone)
  const choices = eligibleRecipients(everyone, homeownerProperties, watchers.property_id)
  const save = useSaveChecklistRecipients()
  // Who hears about it. How they are addressed follows from their role.
  const [chosen, setChosen] = useState(
    () => new Set(watchers.recipients.map((recipient) => recipient.user_id)),
  )
  const [error, setError] = useState<string>()
  const busy = save.isPending
  const picked = choices.filter((member) => chosen.has(member.user_id))

  const toggle = (userId: string) => {
    setError(undefined)
    setChosen((current) => {
      const next = new Set(current)
      if (!next.delete(userId)) {
        next.add(userId)
      }
      return next
    })
  }

  const submit = async () => {
    try {
      await save.mutateAsync({
        propertyId: watchers.property_id,
        recipients: Object.entries(addressing(picked)).map(([user_id, kind]) => ({
          user_id,
          kind,
        })),
      })
    } catch (failure) {
      setError(getErrorMessage(failure))
      return
    }
    onOpenChange(false)
    toast.success(
      picked.length === 0
        ? `Nobody hears about ${watchers.property_name}`
        : `${watchers.property_name} checklists will be sent`,
    )
  }

  return (
    <FormDialog
      title={watchers.property_name}
      open={open}
      onOpenChange={onOpenChange}
      onSubmit={() => void submit()}
      submitLabel="Save"
      pending={busy}
      error={error}
    >
      <p className="text-sm text-muted-foreground">
        A finished checklist is addressed to the owners and copied to everyone else.
      </p>

      <RecipientPicker
        choices={choices}
        chosen={chosen}
        onToggle={toggle}
        loading={members.isPending}
        disabled={busy}
      />
    </FormDialog>
  )
}
