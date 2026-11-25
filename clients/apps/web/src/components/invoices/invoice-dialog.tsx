'use client'

import { useState } from 'react'
import { toast } from 'sonner'

import { ConfirmDialog } from '@/components/confirm-dialog'
import { TextAction } from '@/components/dialog-actions'
import { FieldRow, FieldRows } from '@/components/dialog-fields'
import { FormDialog } from '@/components/form-dialog'
import { useCompany, useCurrency } from '@/components/session-context'
import { invoicePDF, useDeleteInvoice } from '@/hooks/invoices'
import { getErrorMessage } from '@/lib/api/errors'
import type { Invoice } from '@/lib/api/types'
import { formatDate, formatMomentDay, formatMoney } from '@/lib/format'

/**
 * One invoice as it went out. Nothing on it changes once it is emailed: it
 * can be downloaded, or deleted so its guest expenses can be billed again.
 */
export function InvoiceDialog({
  invoice,
  propertyName,
  open,
  onOpenChange,
}: {
  invoice: Invoice
  propertyName?: string
  open: boolean
  onOpenChange: (open: boolean) => void
}) {
  const currency = useCurrency()
  const timezone = useCompany().data?.timezone ?? 'America/Mazatlan'
  const remove = useDeleteInvoice()
  const [confirming, setConfirming] = useState(false)
  const [error, setError] = useState<string>()
  const money = (amount: number) => formatMoney(amount, currency)

  const drop = async () => {
    try {
      await remove.mutateAsync(invoice.id)
    } catch (failure) {
      setError(getErrorMessage(failure))
      return
    }
    setConfirming(false)
    onOpenChange(false)
    toast.success(`Invoice ${invoice.number} deleted`)
  }

  return (
    <>
      <FormDialog
        title={`Invoice ${invoice.number}`}
        open={open && !confirming}
        onOpenChange={onOpenChange}
        onSubmit={() =>
          window.open(invoicePDF(invoice.id), '_blank', 'noopener,noreferrer')
        }
        submitLabel="Download PDF"
        className="max-h-[calc(100dvh-2rem)]"
        actions={
          <TextAction destructive onClick={() => setConfirming(true)}>
            Delete invoice
          </TextAction>
        }
      >
        <FieldRows>
          <FieldRow label="Bill to">
            <span className="truncate">{invoice.recipient_name}</span>
          </FieldRow>
          <FieldRow label="Email">
            <span className="truncate">{invoice.email}</span>
          </FieldRow>
          {propertyName && (
            <FieldRow label="Property">
              <span className="truncate">{propertyName}</span>
            </FieldRow>
          )}
          <FieldRow label="Issued">{formatDate(invoice.issued_on)}</FieldRow>
          <FieldRow label="Due">{formatDate(invoice.due_on)}</FieldRow>
        </FieldRows>

        <FieldRows>
          {invoice.lines.map((line) => (
            <FieldRow key={line.id} label={line.description}>
              <span className="whitespace-nowrap tabular-nums">
                {line.quantity === 1 ? '' : `${line.quantity} × `}
                {money(line.unit_price)}
              </span>
            </FieldRow>
          ))}
        </FieldRows>

        <FieldRows>
          <FieldRow label="Subtotal">
            <span className="tabular-nums">{money(invoice.subtotal)}</span>
          </FieldRow>
          <FieldRow label={`VAT ${Math.round(Number(invoice.tax_rate) * 100)}%`}>
            <span className="tabular-nums">{money(invoice.tax)}</span>
          </FieldRow>
          <FieldRow label="Total">
            <span className="font-semibold tabular-nums">{money(invoice.total)}</span>
          </FieldRow>
        </FieldRows>

        <p className="-mt-2 px-1 text-xs text-muted-foreground">
          {invoice.sent_at
            ? `Emailed ${formatMomentDay(invoice.sent_at, timezone)}.`
            : 'Being emailed now.'}
        </p>
      </FormDialog>

      <ConfirmDialog
        title={`Delete invoice ${invoice.number}`}
        action="Delete invoice"
        open={confirming}
        onOpenChange={setConfirming}
        onConfirm={() => void drop()}
        pending={remove.isPending}
        error={error}
      >
        The guest keeps the email they were sent. Its number is not used again, and its
        guest expenses can be billed on another invoice.
      </ConfirmDialog>
    </>
  )
}
