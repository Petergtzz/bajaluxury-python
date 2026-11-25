import type { schemas } from '@/lib/api/client'
import type { PaymentMethod, RecurringCharge } from '@/lib/api/types'
import { formatDate, sentence } from '@/lib/format'
import { ordinal } from '@/lib/reports'

/** Any day a month has; 31 means its last, whatever that is. */
export const DAYS = Array.from({ length: 31 }, (_, index) => index + 1)

export const dayName = (day: number): string =>
  day === 31 ? 'Last day' : `The ${ordinal(day)}`

export type ChargeDraft = {
  propertyId: string
  amount: string
  category: string
  concept: string
  paymentMethod: PaymentMethod
  day: number
  description: string
}

export const draftFromCharge = (charge: RecurringCharge | null): ChargeDraft => ({
  propertyId: charge?.property_id ?? '',
  amount: charge
    ? charge.amount.toLocaleString('en-US', {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2,
      })
    : '',
  category: charge?.category ?? '',
  concept: charge?.concept ?? '',
  paymentMethod: charge?.payment_method ?? 'cash',
  day: charge?.day_of_month ?? 1,
  description: charge?.description ?? '',
})

/** "1,250.50" as typed, read as the API takes it, or nothing if it isn't one. */
const toAmount = (typed: string): string | null => {
  const amount = typed.replace(/,/g, '').trim()
  return amount !== '' && Number(amount) > 0 ? amount : null
}

/** What is missing before it can be saved, or nothing. */
const problem = (draft: ChargeDraft): string | undefined =>
  (!draft.propertyId && 'Pick the property it is charged to.') ||
  (toAmount(draft.amount) === null && 'Enter the amount.') ||
  (!draft.category.trim() && 'Name the category.') ||
  (!draft.concept.trim() && 'Say what it is.') ||
  undefined

export const toChargeCreate = (
  draft: ChargeDraft,
): { body: schemas['RecurringChargeCreate'] } | { error: string } => {
  const error = problem(draft)
  if (error) return { error }
  return {
    body: {
      property_id: draft.propertyId,
      amount: toAmount(draft.amount) ?? '0',
      category: draft.category.trim(),
      concept: draft.concept.trim(),
      payment_method: draft.paymentMethod,
      day_of_month: draft.day,
      description: draft.description.trim() || null,
    },
  }
}

/** Only what changed: it applies from the next charge on. */
export const toChargeChanges = (
  draft: ChargeDraft,
  charge: RecurringCharge,
): { body: schemas['RecurringChargeUpdate'] } | { error: string } => {
  const result = toChargeCreate(draft)
  if ('error' in result) return result
  const { body } = result
  return {
    body: {
      ...(Number(body.amount) !== charge.amount && { amount: body.amount }),
      ...(body.category !== charge.category && { category: body.category }),
      ...(body.concept !== charge.concept && { concept: body.concept }),
      ...(body.payment_method !== charge.payment_method && {
        payment_method: body.payment_method,
      }),
      ...(body.day_of_month !== charge.day_of_month && {
        day_of_month: body.day_of_month,
      }),
      ...(body.description !== charge.description && { description: body.description }),
    },
  }
}

/** A charge's quiet line: how it is paid, when, and when it next falls. */
export const describeCharge = (charge: RecurringCharge): string =>
  [
    sentence(charge.category),
    sentence(charge.payment_method),
    charge.day_of_month === 31
      ? 'Last day of the month'
      : `On the ${ordinal(charge.day_of_month)}`,
    `next ${formatDate(charge.next_charge_on)}`,
  ].join(' · ')
