'use client'

import { useState } from 'react'
import { toast } from 'sonner'

import { FieldRow, FieldRows, RowSelect, SelectItem } from '@/components/dialog-fields'
import { FormDialog } from '@/components/form-dialog'
import { useSendReport } from '@/hooks/reports'
import { getErrorMessage } from '@/lib/api/errors'
import type { Report } from '@/lib/api/types'
import { describeSend, monthName, sendableMonths } from '@/lib/reports'

/**
 * Send a property's statement now, for a month of your choosing.
 *
 * Only properties that are set up are offered: a statement goes to the people
 * on the report, so one with nobody on it has nowhere to go. The last complete
 * month leads the list, because it is what the schedule would send next and
 * what most sends want; the rest are for an owner who joined late.
 */
export function SendReportDialog({
  reports,
  timezone,
  open,
  onOpenChange,
}: {
  /** Every report on the page; the sendable ones are offered. */
  reports: Report[]
  /** The company's, so the months are counted on its clock. */
  timezone: string
  open: boolean
  onOpenChange: (open: boolean) => void
}) {
  const send = useSendReport()
  const sendable = reports.filter((one) => one.recipients.length > 0)
  const months = sendableMonths(timezone)
  const [propertyId, setPropertyId] = useState(sendable[0]?.property_id ?? '')
  const [month, setMonth] = useState(months[0] ?? '')
  const [error, setError] = useState<string>()

  const chosen = (value: string) => {
    setError(undefined)
    return value
  }

  const submit = async () => {
    try {
      const sent = await send.mutateAsync({ propertyId, month })
      onOpenChange(false)
      toast.success(describeSend(sent.month, sent.recipient_count))
    } catch (failure) {
      setError(getErrorMessage(failure))
    }
  }

  return (
    <FormDialog
      title="Send report"
      open={open}
      onOpenChange={onOpenChange}
      onSubmit={() => void submit()}
      submitLabel="Send statement"
      pending={send.isPending}
      disabled={propertyId === '' || month === ''}
      error={error}
    >
      <FieldRows>
        <FieldRow label="Property">
          <RowSelect
            label="Property"
            value={propertyId}
            onValueChange={(value) => setPropertyId(chosen(value))}
            placeholder="Select"
            disabled={send.isPending}
          >
            {sendable.map((one) => (
              <SelectItem key={one.property_id} value={one.property_id}>
                {one.property_name}
              </SelectItem>
            ))}
          </RowSelect>
        </FieldRow>
        <FieldRow label="Month">
          <RowSelect
            label="Month to send"
            value={month}
            onValueChange={(value) => setMonth(chosen(value))}
            placeholder="Select"
            disabled={send.isPending}
          >
            {months.map((one) => (
              <SelectItem key={one} value={one}>
                {monthName(one)}
              </SelectItem>
            ))}
          </RowSelect>
        </FieldRow>
      </FieldRows>

      {sendable.length === 0 ? (
        <p className="px-1 text-sm text-muted-foreground">
          No property is set up to report yet. Choose who receives one first.
        </p>
      ) : (
        <p className="px-1 text-sm text-muted-foreground">
          Sending the same month twice replaces the first send rather than adding a
          second.
        </p>
      )}
    </FormDialog>
  )
}
