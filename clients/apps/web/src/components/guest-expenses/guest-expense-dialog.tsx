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
  useCreateGuestExpense,
  useDeleteGuestExpense,
  useUpdateGuestExpense,
} from '@/hooks/guest-expenses'
import { ClientResponseError, type schemas } from '@/lib/api/client'
import { getErrorMessage, setValidationErrors } from '@/lib/api/errors'
import type { Property } from '@/lib/api/types'
import { formatDate } from '@/lib/format'

type GuestExpense = schemas['GuestExpenseSchema']

type Values = {
  amount: string
  date: string
  property_id: string
  category: string
  concept: string
  description: string
}

/**
 * One thing bought for a renting guest, to record or correct. Billing it is
 * the invoice's job; here it only says whether that has happened.
 */
export function GuestExpenseDialog({
  guestExpense,
  open,
  onOpenChange,
  today,
  properties,
  categories,
  currency,
  readOnly,
}: {
  guestExpense: GuestExpense | null
  open: boolean
  onOpenChange: (open: boolean) => void
  today: string
  properties: Property[]
  categories: string[]
  currency: string
  readOnly: boolean
}) {
  const create = useCreateGuestExpense()
  const update = useUpdateGuestExpense()
  const remove = useDeleteGuestExpense()
  const active = properties.filter((p) => !p.is_archived)
  const form = useForm<Values>({
    defaultValues: guestExpense
      ? {
          amount: guestExpense.amount.toLocaleString('en-US', {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2,
          }),
          date: guestExpense.date,
          property_id: guestExpense.property_id,
          category: guestExpense.category,
          concept: guestExpense.concept,
          description: guestExpense.description ?? '',
        }
      : {
          amount: '',
          date: today,
          property_id: active.length === 1 ? (active[0]?.id ?? '') : '',
          category: '',
          concept: '',
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
      amount: values.amount.replace(/,/g, '').trim(),
      description: values.description.trim() || null,
    }
    try {
      if (guestExpense) {
        await update.mutateAsync({ id: guestExpense.id, body })
        toast.success('Guest expense saved')
      } else {
        await create.mutateAsync(body)
        toast.success('Guest expense recorded')
      }
      onOpenChange(false)
    } catch (error) {
      if (error instanceof ClientResponseError) setValidationErrors(error, form.setError)
      else form.setError('root', { message: getErrorMessage(error) })
    }
  })

  const destroy = async () => {
    if (!guestExpense) return
    try {
      await remove.mutateAsync(guestExpense.id)
      toast.success('Guest expense deleted')
      onOpenChange(false)
    } catch (error) {
      toast.error(getErrorMessage(error))
    }
  }

  const propertyName = (id: string) => properties.find((p) => p.id === id)?.name ?? ''

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent
        aria-describedby={undefined}
        onOpenAutoFocus={(event) => guestExpense && event.preventDefault()}
      >
        <DialogTitle className="sr-only">
          {guestExpense ? 'Guest expense' : 'Add guest expense'}
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
                    <>{propertyName(field.value)}</>
                  ) : (
                    <RowSelect
                      label="Property"
                      value={field.value}
                      onValueChange={field.onChange}
                    >
                      {(guestExpense ? properties : active).map((p) => (
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
                list="guest-categories"
                placeholder="transport"
                readOnly={readOnly}
                {...form.register('category', { required: 'Name the category.' })}
              />
              <datalist id="guest-categories">
                {categories.map((category) => (
                  <option key={category} value={category} />
                ))}
              </datalist>
            </FieldRow>
            <FieldRow label="Concept">
              <RowInput
                placeholder="airport pickup"
                readOnly={readOnly}
                {...form.register('concept', { required: 'Say what it was.' })}
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

          {guestExpense && (
            <DialogDescription className="text-center">
              {guestExpense.invoice_id
                ? 'Billed to the guest on an invoice.'
                : 'Not billed to the guest yet.'}
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
                {guestExpense ? 'Save changes' : 'Record guest expense'}
              </Button>
              {guestExpense && (
                <DeleteAction
                  label="Delete guest expense"
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
