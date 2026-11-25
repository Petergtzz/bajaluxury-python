import type { PaymentMethod, Property } from '@/lib/api/types'
import { serializeFilters } from '@/lib/ledger/filters'
import type { Period, Range } from '@/lib/period'

/** What the dashboard shows, as the address carries it. Empty is the default. */
export type DashboardFilters = { property: string; month: string }

const MONTH = /^\d{4}-(0[1-9]|1[0-2])$/

export const parseDashboardFilters = (params: URLSearchParams): DashboardFilters => {
  const month = params.get('month') ?? ''
  return { property: params.get('property') ?? '', month: MONTH.test(month) ? month : '' }
}

/** The address for filters; the first house and this month are left out. */
export function serializeDashboardFilters(filters: DashboardFilters): string {
  const params = new URLSearchParams()
  if (filters.property) params.set('property', filters.property)
  if (filters.month) params.set('month', filters.month)
  return params.toString()
}

const byName = (a: Property, b: Property) => a.name.localeCompare(b.name)

/** The houses to pick from: those in use, and the one asked for even if archived. */
export const dashboardProperties = (properties: Property[], asked: string): Property[] =>
  properties.filter((p) => !p.is_archived || p.id === asked).toSorted(byName)

/** The house shown: the one asked for, else the first in use by name. */
export const chooseProperty = (
  properties: Property[],
  asked: string,
): Property | undefined =>
  properties.find((p) => p.id === asked) ??
  properties.filter((p) => !p.is_archived).toSorted(byName)[0]

const pad = (n: number) => String(n).padStart(2, '0')

const shift = (month: string, by: number): string => {
  const [year = 0, number = 1] = month.split('-').map(Number)
  const index = year * 12 + number - 1 + by
  return `${Math.floor(index / 12)}-${pad((index % 12) + 1)}`
}

/** The month shown, `YYYY-MM`: the one asked for, else today's. */
export const shownMonth = (filters: DashboardFilters, today: string): string =>
  filters.month && filters.month <= today.slice(0, 7) ? filters.month : today.slice(0, 7)

/**
 * The months a house can be looked at, newest first: from its first entry to
 * today's, empty ones too, so a quiet month reads as nothing rather than gone.
 */
export function monthsOf(firstEntry: string | null | undefined, today: string): string[] {
  const now = today.slice(0, 7)
  const first = firstEntry && firstEntry.slice(0, 7) < now ? firstEntry.slice(0, 7) : now
  const months = [now]
  while (months.at(-1)! > first) months.push(shift(months.at(-1)!, -1))
  return months
}

/** A month's days, both included. */
export function monthRange(month: string): Range {
  const [year = 0, number = 1] = month.split('-').map(Number)
  return {
    from: `${month}-01`,
    to: `${month}-${pad(new Date(year, number, 0).getDate())}`,
  }
}

const LABEL = new Intl.DateTimeFormat('en-GB', { month: 'long', year: 'numeric' })
const SHORT = new Intl.DateTimeFormat('en-GB', { month: 'long' })

/** "July 2026". */
export const monthLabel = (month: string): string => {
  const [year = 0, number = 1] = month.split('-').map(Number)
  return LABEL.format(new Date(year, number - 1, 1))
}

/** "July", for a figure that sits under the month's own chip. */
export const monthName = (month: string): string => {
  const [year = 0, number = 1] = month.split('-').map(Number)
  return SHORT.format(new Date(year, number - 1, 1))
}

/** Which of a house's expenses a row stands for. */
export type ExpenseNarrow = { category?: string; method?: PaymentMethod }

/**
 * The expenses behind a row, on Transactions with the same house and month:
 * named "this month" or "last month" where Transactions has those, so its chip
 * reads the way people say it.
 */
export function expensesHref(
  month: string,
  today: string,
  propertyId: string,
  narrow: ExpenseNarrow,
): string {
  const now = today.slice(0, 7)
  const period: Period =
    month === now ? 'this-month' : month === shift(now, -1) ? 'last-month' : 'custom'
  const range = period === 'custom' ? monthRange(month) : { from: '', to: '' }
  return `/transactions?${serializeFilters({
    period,
    ...range,
    property: propertyId,
    type: 'expense',
    method: narrow.method ?? '',
    category: narrow.category ?? '',
  })}`
}

/** A part of the whole as a whole percentage, "<1%" rather than a misleading 0%. */
export function share(part: number, whole: number): string {
  if (whole <= 0) return '0%'
  const percent = (part / whole) * 100
  return percent > 0 && percent < 1 ? '<1%' : `${Math.round(percent)}%`
}
