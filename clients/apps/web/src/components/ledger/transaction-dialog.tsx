'use client'

import { Controller, useForm } from 'react-hook-form'
import { toast } from 'sonner'

import { DeleteAction } from '@/components/delete-action'
import {
  AmountField,
  FieldRow,
  FieldRows,
  RowDateInput,
  RowInput,
  RowSelect,
} from '@/components/dialog-fields'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogTitle,
} from '@/components/ui/dialog'
import { SelectItem } from '@/components/ui/select'
import { Spinner } from '@/components/ui/spinner'
import {
  useCreateTransaction,
  useDeleteTransaction,
  useUpdateTransaction,
} from '@/hooks/ledger'
import { ClientResponseError } from '@/lib/api/client'
import { getErrorMessage, setValidationErrors } from '@/lib/api/errors'
import type {
  PaymentMethod,
  Property,
  Transaction,
  TransactionType,
} from '@/lib/api/types'
import { formatDate, sentence } from '@/lib/format'
import { METHODS } from '@/lib/ledger/filters'

type Values = {
  amount: string
  type: TransactionType
  date: string
  property_id: string
  category: string
  concept: string
  payment_method: PaymentMethod | ''
  description: string
}

const TYPE_NAMES: Record<TransactionType, string> = {
  expense: 'Money out',
  income: 'Money in',
}

/** "1,250.50" as typed, read as the API takes it. */
const toAmount = (typed: string) => typed.replace(/,/g, '').trim()

/**
 * One transaction, to record or to correct: the amount large at the top, the
 * rest as rows. Someone who only reads the books gets the same card, read-only.
 */
export function TransactionDialog({
  transaction,
  open,
  onOpenChange,
  today,
  properties,
  categories,
  currency,
  readOnly,
}: {
  /** Null to record a new one. */
  transaction: Transaction | null
  open: boolean
  onOpenChange: (open: boolean) => void
  today: string
  properties: Property[]
  categories: string[]
  currency: string
  readOnly: boolean
}) {
  const create = useCreateTransaction()
  const update = useUpdateTransaction()
  const remove = useDeleteTransaction()
  const open_ = properties.filter((p) => !p.is_archived)
  const form = useForm<Values>({
    defaultValues: transaction
      ? {
          amount: transaction.amount.toLocaleString('en-US', {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2,
          }),
          type: transaction.type,
          date: transaction.date,
          property_id: transaction.property_id,
          category: transaction.category,
          concept: transaction.concept,
          payment_method: transaction.payment_method ?? '',
          description: transaction.description ?? '',
        }
      : {
          amount: '',
          type: 'expense',
          date: today,
          property_id: open_.length === 1 ? (open_[0]?.id ?? '') : '',
          category: '',
          concept: '',
          payment_method: 'cash',
          description: '',
        },
  })
  const errors = form.formState.errors
  const problems = Object.values(errors)
    .map((error) => error?.message)
    .filter(Boolean)

  const save = form.handleSubmit(async (values) => {
    const body = {
      ...values,
      amount: toAmount(values.amount),
      payment_method: values.payment_method || undefined,
      description: values.description.trim() || null,
    }
    try {
      if (transaction) {
        await update.mutateAsync({ id: transaction.id, body })
        toast.success('Transaction saved')
      } else {
        await create.mutateAsync(body as never)
        toast.success('Transaction recorded')
      }
      onOpenChange(false)
    } catch (error) {
      if (error instanceof ClientResponseError) setValidationErrors(error, form.setError)
      else form.setError('root', { message: getErrorMessage(error) })
    }
  })

  const destroy = async () => {
    if (!transaction) return
    try {
      await remove.mutateAsync(transaction.id)
      toast.success('Transaction deleted')
      onOpenChange(false)
    } catch (error) {
      toast.error(getErrorMessage(error))
    }
  }

  const property = (id: string) => properties.find((p) => p.id === id)?.name ?? ''

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent
        aria-describedby={undefined}
        onOpenAutoFocus={(e) => transaction && e.preventDefault()}
      >
        <DialogTitle className="sr-only">
          {transaction ? 'Transaction' : 'Add transaction'}
        </DialogTitle>
        <form onSubmit={save} className="flex flex-col gap-5" noValidate>
          <AmountField
            currency={currency}
            readOnly={readOnly}
            invalid={!!errors.amount}
            {...form.register('amount', { required: 'Enter the amount.' })}
            value={form.watch('amount')}
          />
          <FieldRows>
            <FieldRow label="Type">
              <Controller
                control={form.control}
                name="type"
                render={({ field }) => (
                  <RowSelect
                    label="Type"
                    value={field.value}
                    onChange={field.onChange}
                    disabled={readOnly}
                  >
                    {(['expense', 'income'] as const).map((type) => (
                      <SelectItem key={type} value={type}>
                        {TYPE_NAMES[type]}
                      </SelectItem>
                    ))}
                  </RowSelect>
                )}
              />
            </FieldRow>
            <FieldRow label="Date">
              {readOnly ? (
                formatDate(form.getValues('date'))
              ) : (
                <RowDateInput
                  {...form.register('date', { required: 'Pick the date.' })}
                />
              )}
            </FieldRow>
            <FieldRow label="Property">
              <Controller
                control={form.control}
                name="property_id"
                rules={{ required: 'Pick the property.' }}
                render={({ field }) =>
                  readOnly ? (
                    <>{property(field.value)}</>
                  ) : (
                    <RowSelect
                      label="Property"
                      value={field.value}
                      onChange={field.onChange}
                    >
                      {(transaction ? properties : open_).map((p) => (
                        <SelectItem key={p.id} value={p.id}>
                          {p.name}
                        </SelectItem>
                      ))}
                    </RowSelect>
                  )
                }
              />
            </FieldRow>
            <FieldRow label="Category">
              <RowInput
                list="categories"
                placeholder="utilities"
                readOnly={readOnly}
                {...form.register('category', { required: 'Name the category.' })}
              />
              <datalist id="categories">
                {categories.map((category) => (
                  <option key={category} value={category} />
                ))}
              </datalist>
            </FieldRow>
            <FieldRow label="Concept">
              <RowInput
                placeholder="cfe"
                readOnly={readOnly}
                {...form.register('concept', { required: 'Say what it was.' })}
              />
            </FieldRow>
            <FieldRow label="Paid with">
              <Controller
                control={form.control}
                name="payment_method"
                render={({ field }) => (
                  <RowSelect
                    label="Paid with"
                    value={field.value}
                    onChange={field.onChange}
                    placeholder="Not recorded"
                    disabled={readOnly}
                  >
                    {METHODS.map((method) => (
                      <SelectItem key={method} value={method}>
                        {sentence(method)}
                      </SelectItem>
                    ))}
                  </RowSelect>
                )}
              />
            </FieldRow>
            <FieldRow label="Note">
              <RowInput
                placeholder={readOnly ? 'None' : 'Add a note'}
                readOnly={readOnly}
                {...form.register('description')}
              />
            </FieldRow>
          </FieldRows>

          {transaction && (
            <DialogDescription className="text-center">
              {transaction.affects_balance
                ? 'This moved the owner’s balance with us.'
                : 'Paid from the owner’s own account: their balance with us is unchanged.'}
            </DialogDescription>
          )}

          {problems.length > 0 && (
            <ul className="flex flex-col gap-1 text-center text-sm text-destructive">
              {problems.map((problem) => (
                <li key={problem}>{problem}</li>
              ))}
            </ul>
          )}

          {!readOnly && (
            <div className="flex flex-col items-center gap-3">
              <Button
                type="submit"
                size="lg"
                className="w-full"
                disabled={form.formState.isSubmitting}
              >
                {form.formState.isSubmitting && <Spinner />}
                {transaction ? 'Save changes' : 'Record transaction'}
              </Button>
              {transaction && (
                <DeleteAction
                  label="Delete transaction"
                  busy={remove.isPending}
                  onDelete={destroy}
                />
              )}
            </div>
          )}
        </form>
      </DialogContent>
    </Dialog>
  )
}
