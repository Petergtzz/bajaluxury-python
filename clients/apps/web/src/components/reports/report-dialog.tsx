'use client'

import { useState } from 'react'
import { toast } from 'sonner'

import { FieldRow, Panel, RowSelect, SelectItem } from '@/components/dialog-fields'
import { TextAction } from '@/components/dialog-actions'
import { FormDialog } from '@/components/form-dialog'
import { RecipientPicker } from '@/components/recipient-picker'
import { useSaveReport, useTurnOffReport } from '@/hooks/reports'
import { useHomeownerProperties, useMembers } from '@/hooks/team'
import { getErrorMessage } from '@/lib/api/errors'
import type { Report } from '@/lib/api/types'
import { addressing, eligibleRecipients, ordinal, SEND_DAYS } from '@/lib/reports'

/**
 * Who receives one property's monthly report.
 *
 * A list of the people who can see the property, ticked or not. Saving with
 * nobody ticked is the same as turning the report off, so there is one control
 * and not a switch beside it.
 */
export function ReportDialog({
  report,
  open,
  onOpenChange,
}: {
  report: Report
  open: boolean
  onOpenChange: (open: boolean) => void
}) {
  const members = useMembers()
  const everyone = members.data ?? []
  const homeownerProperties = useHomeownerProperties(everyone)
  const choices = eligibleRecipients(everyone, homeownerProperties, report.property_id)
  const saveReport = useSaveReport()
  const turnOff = useTurnOffReport()
  // Who is on the report. How they are addressed follows from their role.
  const [chosen, setChosen] = useState(
    () => new Set(report.recipients.map((recipient) => recipient.user_id)),
  )
  const [sendDay, setSendDay] = useState(report.send_day)
  const [error, setError] = useState<string>()
  const busy = saveReport.isPending || turnOff.isPending
  const wasOn = report.recipients.length > 0
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

  const save = async () => {
    try {
      if (picked.length === 0) {
        if (wasOn) {
          await turnOff.mutateAsync(report.property_id)
        }
      } else {
        await saveReport.mutateAsync({
          propertyId: report.property_id,
          recipients: Object.entries(addressing(picked)).map(([user_id, kind]) => ({
            user_id,
            kind,
          })),
          sendDay,
        })
      }
    } catch (failure) {
      setError(getErrorMessage(failure))
      return
    }
    onOpenChange(false)
    toast.success(
      picked.length === 0
        ? `${report.property_name} stopped sending reports`
        : `${report.property_name} reports monthly`,
    )
  }

  const stop = async () => {
    try {
      await turnOff.mutateAsync(report.property_id)
    } catch (failure) {
      setError(getErrorMessage(failure))
      return
    }
    onOpenChange(false)
    toast.success(`${report.property_name} stopped sending reports`)
  }

  return (
    <FormDialog
      title={report.property_name}
      open={open}
      onOpenChange={onOpenChange}
      onSubmit={() => void save()}
      submitLabel={picked.length === 0 && wasOn ? 'Turn off' : 'Save'}
      pending={busy}
      disabled={picked.length === 0 && !wasOn}
      error={error}
      actions={
        // With nobody ticked, the button itself already says Turn off.
        wasOn &&
        picked.length > 0 && (
          <TextAction destructive onClick={() => void stop()} disabled={busy}>
            Turn off
          </TextAction>
        )
      }
    >
      <p className="text-sm text-muted-foreground">
        The statement is addressed to the owners and copied to everyone else.
      </p>

      <RecipientPicker
        choices={choices}
        chosen={chosen}
        onToggle={toggle}
        loading={members.isPending}
        disabled={busy}
      />

      <Panel>
        <FieldRow label="Send on the">
          <RowSelect
            label="Day of the month"
            value={String(sendDay)}
            onValueChange={(value) => setSendDay(Number(value))}
            placeholder="1st"
            disabled={busy}
          >
            {SEND_DAYS.map((day) => (
              <SelectItem key={day} value={String(day)}>
                {ordinal(day)}
              </SelectItem>
            ))}
          </RowSelect>
        </FieldRow>
      </Panel>
      <p className="-mt-2 px-1 text-xs text-muted-foreground">
        Of the month after the one it covers.
      </p>
    </FormDialog>
  )
}
