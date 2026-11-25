import type { PaymentMethod, Property } from '@/lib/api/types'
import { formatDate } from '@/lib/format'
import { serializeFilters } from '@/lib/ledger/filters'
import {
  customRange,
  getRange,
  type PeriodChoice,
  type PeriodFilter,
  type Range,
  readPeriod,
  writePeriod,
} from '@/lib/period'

/** A statement needs both ends, so "all time" isn't offered. */
export const DASHBOARD_PERIODS: PeriodChoice = {
  fallback: 'this-month',
  allowed: ['this-month', 'last-month', 'this-year', 'custom'],
}

/** What the dashboard shows, as the address carries it. */
export type DashboardFilters = PeriodFilter & { property: string }

export const parseDashboardFilters = (params: URLSearchParams): DashboardFilters => ({
  ...readPeriod(params, DASHBOARD_PERIODS),
  property: params.get('property') ?? '',
})

/** The address for filters; the first house and this month are left out. */
export function serializeDashboardFilters(filters: DashboardFilters): string {
  const params = new URLSearchParams()
  writePeriod(params, filters, DASHBOARD_PERIODS)
  if (filters.property) params.set('property', filters.property)
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

/** The days shown, both included; readPeriod already refused what has no ends. */
export const dashboardRange = (filters: DashboardFilters, today: string): Range =>
  getRange(filters.period, today, customRange(filters)) ??
  (getRange('this-month', today) as Range)

/**
 * The closing balance, named for the day it is on: a period still running
 * ends after today, but nothing has happened after today yet.
 */
export const balanceLabel = (range: Range, today: string): string =>
  range.to >= today ? 'Balance today' : `Balance on ${formatDate(range.to)}`

/** Which of a house's expenses a row stands for. */
export type ExpenseNarrow = { category?: string; method?: PaymentMethod }

/** The expenses behind a figure, on Transactions with the same house and days. */
export const expensesHref = (
  filters: DashboardFilters,
  propertyId: string,
  narrow: ExpenseNarrow,
): string =>
  `/transactions?${serializeFilters({
    period: filters.period,
    from: filters.from,
    to: filters.to,
    property: propertyId,
    type: 'expense',
    method: narrow.method ?? '',
    category: narrow.category ?? '',
  })}`

/** A part of the whole as a whole percentage, "<1%" rather than a misleading 0%. */
export function share(part: number, whole: number): string {
  if (whole <= 0) return '0%'
  const percent = (part / whole) * 100
  return percent > 0 && percent < 1 ? '<1%' : `${Math.round(percent)}%`
}
