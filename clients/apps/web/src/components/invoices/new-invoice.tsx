'use client'

import { Plus, ReceiptText, X } from 'lucide-react'
import { useRouter } from 'next/navigation'
import { type ComponentProps, useState } from 'react'
import { toast } from 'sonner'

import {
  FieldRow,
  FieldRows,
  Panel,
  RowDateInput,
  RowInput,
  RowSelect,
  SelectItem,
} from '@/components/dialog-fields'
import { InputError } from '@/components/input-error'
import { ListHeading } from '@/components/list-heading'
import { PageHeader } from '@/components/page-header'
import { useCompany, useCurrency } from '@/components/session-context'
import { Button } from '@/components/ui/button'
import { Spinner } from '@/components/ui/spinner'
import { useCreateInvoice, useUnbilledGuestExpenses } from '@/hooks/invoices'
import { useProperties } from '@/hooks/ledger'
import { getErrorMessage } from '@/lib/api/errors'
import { formatMoney, todayIn } from '@/lib/format'
import {
  blankLine,
  DEFAULT_NOTES,
  type Line,
  lineCents,
  lineFor,
  lineProblem,
  TAX_RATE,
  toLinesBody,
  totals,
} from '@/lib/invoices'
import { cn } from '@/lib/utils'

import { GuestExpensePicker } from './guest-expense-picker'

/**
 * An invoice for a guest, sent the moment it is made.
 *
 * Most bill what was bought for a stay, so the property's unbilled guest
 * expenses are a click away; any line can be typed as well. The totals are
 * worked out here as the server will, so what is shown is what is sent.
 */
export function NewInvoice() {
  const router = useRouter()
  const company = useCompany()
  const currency = useCurrency()
  const today = todayIn(company.data?.timezone ?? 'America/Mazatlan')
  const properties = (useProperties().data ?? []).filter((one) => !one.is_archived)
  const create = useCreateInvoice()

  const [propertyId, setPropertyId] = useState('')
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [issuedOn, setIssuedOn] = useState(today)
  const [dueOn, setDueOn] = useState(today)
  const [rate, setRate] = useState('')
  const [notes, setNotes] = useState(DEFAULT_NOTES)
  const [paymentDetails, setPaymentDetails] = useState('')
  const [lines, setLines] = useState<Line[]>([])
  const [picking, setPicking] = useState(false)
  const [error, setError] = useState<string>()

  const unbilled = useUnbilledGuestExpenses(propertyId)
  const onInvoice = new Set(lines.map((line) => line.guestExpenseId))
  const offered = (unbilled.data ?? []).filter((one) => !onInvoice.has(one.id))
  const sums = totals(lines)
  const exchangeRate = Number(rate || company.data?.usd_exchange_rate || 0)

  const change = (key: string, patch: Partial<Line>) => {
    setError(undefined)
    setLines((current) =>
      current.map((line) => (line.key === key ? { ...line, ...patch } : line)),
    )
  }

  const submit = async () => {
    const problem =
      (!propertyId && 'Pick the property the stay was at.') ||
      (!name.trim() && 'Say who it is for.') ||
      (!email.trim() && 'Give the address it is emailed to.') ||
      (lines.length === 0 && 'Add at least one line.') ||
      lines.map(lineProblem).find(Boolean) ||
      (dueOn < issuedOn && 'It can’t be due before it is issued.') ||
      undefined
    if (problem) {
      setError(problem)
      return
    }
    try {
      const invoice = await create.mutateAsync({
        property_id: propertyId,
        recipient_name: name.trim(),
        email: email.trim(),
        issued_on: issuedOn,
        due_on: dueOn,
        tax_rate: TAX_RATE,
        exchange_rate: rate ? Number(rate) : null,
        notes: notes.trim() || null,
        payment_details: paymentDetails.trim() || null,
        lines: toLinesBody(lines),
      })
      toast.success(`Invoice ${invoice.number} is on its way to ${invoice.email}`)
      router.push('/invoices')
    } catch (failure) {
      setError(getErrorMessage(failure))
    }
  }

  return (
    <>
      <PageHeader
        title="New invoice"
        description="Emailed to the guest as a PDF when you send it."
      />

      <form
        className="flex flex-col gap-8"
        noValidate
        onSubmit={(event) => {
          event.preventDefault()
          void submit()
        }}
      >
        <FieldRows>
          <FieldRow label="Property">
            <RowSelect
              label="Property"
              value={propertyId}
              onValueChange={(value) => {
                setError(undefined)
                setPropertyId(value)
                // Another property's expenses can't go on this one's invoice.
                setLines((current) =>
                  current.filter((line) => line.guestExpenseId === null),
                )
              }}
              placeholder="Select"
            >
              {properties.map((property) => (
                <SelectItem key={property.id} value={property.id}>
                  {property.name}
                </SelectItem>
              ))}
            </RowSelect>
          </FieldRow>
          <FieldRow label="Bill to">
            <RowInput
              value={name}
              onChange={(event) => setName(event.target.value)}
              placeholder="Guest's name"
              maxLength={255}
            />
          </FieldRow>
          <FieldRow label="Email">
            <RowInput
              type="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              placeholder="guest@example.com"
            />
          </FieldRow>
          <FieldRow label="Issued">
            <RowDateInput
              value={issuedOn}
              onChange={(event) => setIssuedOn(event.target.value)}
            />
          </FieldRow>
          <FieldRow label="Due">
            <RowDateInput
              value={dueOn}
              onChange={(event) => setDueOn(event.target.value)}
            />
          </FieldRow>
        </FieldRows>

        <section aria-label="Lines" className="flex flex-col gap-3">
          <ListHeading>Lines</ListHeading>
          {lines.map((line) => (
            <LineEditor
              key={line.key}
              line={line}
              currency={currency}
              onChange={(patch) => change(line.key, patch)}
              onRemove={() =>
                setLines((current) => current.filter((one) => one.key !== line.key))
              }
            />
          ))}
          <div className="flex flex-wrap gap-2">
            {offered.length > 0 && (
              <Button type="button" variant="secondary" onClick={() => setPicking(true)}>
                <ReceiptText />
                Bill guest expenses ({offered.length})
              </Button>
            )}
            <Button
              type="button"
              variant="secondary"
              onClick={() => setLines((current) => [...current, blankLine()])}
            >
              <Plus />
              Add line
            </Button>
          </div>
        </section>

        <FieldRows>
          <FieldRow label="Subtotal">
            <span className="tabular-nums">{formatMoney(sums.subtotal, currency)}</span>
          </FieldRow>
          <FieldRow label={`VAT ${Math.round(TAX_RATE * 100)}%`}>
            <span className="tabular-nums">{formatMoney(sums.tax, currency)}</span>
          </FieldRow>
          <FieldRow label="Total">
            <span className="flex flex-col items-end">
              <span className="font-semibold tabular-nums">
                {formatMoney(sums.total, currency)}
              </span>
              {exchangeRate > 0 && (
                <span className="text-xs text-muted-foreground tabular-nums">
                  {formatMoney(sums.total / exchangeRate, 'USD')}
                </span>
              )}
            </span>
          </FieldRow>
        </FieldRows>

        <FieldRows>
          <FieldRow label="Exchange rate">
            <RowInput
              inputMode="decimal"
              value={rate}
              onChange={(event) => setRate(event.target.value)}
              placeholder={
                company.data
                  ? `${Number(company.data.usd_exchange_rate)} ${currency} per USD`
                  : ''
              }
            />
          </FieldRow>
          <FieldRow label="Notes">
            <RowInput
              value={notes}
              onChange={(event) => setNotes(event.target.value)}
              placeholder="Shown at the foot"
              maxLength={2000}
            />
          </FieldRow>
          <FieldRow label="Payment details">
            <RowInput
              value={paymentDetails}
              onChange={(event) => setPaymentDetails(event.target.value)}
              placeholder="How to pay"
              maxLength={2000}
            />
          </FieldRow>
        </FieldRows>

        <div className="flex flex-col gap-3">
          <InputError message={error} className="text-center" />
          <Button
            type="submit"
            disabled={create.isPending}
            className="h-12 w-full rounded-full text-base font-semibold"
          >
            {create.isPending && <Spinner className="size-5" />}
            Send invoice
          </Button>
        </div>
      </form>

      {picking && (
        <GuestExpensePicker
          expenses={offered}
          currency={currency}
          open
          onOpenChange={setPicking}
          onPick={(picked) => {
            setError(undefined)
            setLines((current) => [
              // A blank line nobody typed into is in the way of what was picked.
              ...current.filter((line) => line.description || line.unitPrice),
              ...picked.map(lineFor),
            ])
          }}
        />
      )}
    </>
  )
}

const BOX =
  'min-w-0 rounded-lg bg-transparent text-[15px] outline-none placeholder:text-muted-foreground'

function LineEditor({
  line,
  currency,
  onChange,
  onRemove,
}: {
  line: Line
  currency: string
  onChange: (patch: Partial<Line>) => void
  onRemove: () => void
}) {
  const label = line.description || 'New line'
  return (
    <Panel className="flex flex-col gap-2 py-3 pr-3">
      <div className="flex items-center gap-2">
        <input
          aria-label="Description"
          value={line.description}
          onChange={(event) => onChange({ description: event.target.value })}
          placeholder="What it was"
          maxLength={255}
          className={cn(BOX, 'flex-1')}
        />
        <Button
          type="button"
          variant="ghost"
          size="icon"
          className="size-8 shrink-0 rounded-full text-muted-foreground"
          aria-label={`Remove ${label}`}
          onClick={onRemove}
        >
          <X />
        </Button>
      </div>
      <div className="flex items-center gap-2 pr-2 text-[15px] text-muted-foreground">
        <NumberBox
          aria-label={`Quantity of ${label}`}
          value={line.quantity}
          onChange={(event) => onChange({ quantity: event.target.value })}
          className="w-12"
        />
        <span aria-hidden>×</span>
        <NumberBox
          aria-label={`Price of ${label}`}
          value={line.unitPrice}
          onChange={(event) => onChange({ unitPrice: event.target.value })}
          placeholder="0.00"
          className="w-28"
        />
        <span className="ml-auto font-medium whitespace-nowrap text-foreground tabular-nums">
          {formatMoney(lineCents(line) / 100, currency)}
        </span>
      </div>
    </Panel>
  )
}

function NumberBox({ className, ...props }: ComponentProps<'input'>) {
  return (
    <input
      inputMode="decimal"
      className={cn(
        BOX,
        'bg-white px-2 py-1 text-foreground tabular-nums dark:bg-neutral-900',
        className,
      )}
      {...props}
    />
  )
}
