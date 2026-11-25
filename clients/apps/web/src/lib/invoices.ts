import type { GuestExpense } from '@/lib/api/types'
import { sentence } from '@/lib/format'

/** Mexican VAT, which every invoice so far has carried. */
export const TAX_RATE = 0.16

/** What every invoice has said at its foot. */
export const DEFAULT_NOTES = 'Tip for staff is not included.'

export type Line = {
  /** Only for React: lines have no identity until they are sent. */
  key: string
  description: string
  quantity: string
  unitPrice: string
  guestExpenseId: string | null
}

let next = 0
export const blankLine = (): Line => ({
  key: `line-${++next}`,
  description: '',
  quantity: '1',
  unitPrice: '',
  guestExpenseId: null,
})

/** A guest expense, billed as one line at what it cost. */
export const lineFor = (expense: GuestExpense): Line => ({
  ...blankLine(),
  description: sentence(expense.description || expense.concept),
  unitPrice: String(expense.amount),
  guestExpenseId: expense.id,
})

/** A number typed into a box, or nothing if it isn't one. */
const parse = (value: string): number | null => {
  const number = Number(value.replace(/,/g, ''))
  return value.trim() === '' || !Number.isFinite(number) ? null : number
}

/**
 * Cents, rounded half up as the server rounds them, so the total shown is the
 * total sent. Whole cents keep floating point from drifting a sum.
 */
const toCents = (value: number) => Math.round(Number((value * 100).toFixed(6)))

export const lineCents = (line: Line): number => {
  const quantity = parse(line.quantity) ?? 0
  const price = parse(line.unitPrice) ?? 0
  return Math.round(Number((quantity * toCents(price)).toFixed(6)))
}

export const totals = (lines: Line[]) => {
  const subtotal = lines.reduce((sum, line) => sum + lineCents(line), 0)
  const tax = Math.round(Number((subtotal * TAX_RATE).toFixed(6)))
  return { subtotal: subtotal / 100, tax: tax / 100, total: (subtotal + tax) / 100 }
}

/** What is wrong with a line, or nothing. Said before it reaches the server. */
export const lineProblem = (line: Line): string | undefined => {
  const quantity = parse(line.quantity)
  const price = parse(line.unitPrice)
  if (!line.description.trim()) return 'Every line needs a description.'
  if (quantity === null || quantity <= 0) return 'Every quantity is more than nothing.'
  if (price === null || price < 0) return 'Every line needs a price.'
  return undefined
}

/** The lines as the API takes them. */
export const toLinesBody = (lines: Line[]) =>
  lines.map((line) => ({
    description: line.description.trim(),
    quantity: parse(line.quantity) ?? 1,
    unit_price: parse(line.unitPrice) ?? 0,
    guest_expense_id: line.guestExpenseId,
  }))
