import {
  getRange,
  type PeriodChoice,
  type PeriodFilter,
  readPeriod,
  writePeriod,
} from '@/lib/period'

/** A report covers finished stretches: a month, the year, or days of one's own. */
export const STATEMENT_PERIODS: PeriodChoice = {
  fallback: 'last-month',
  allowed: ['this-month', 'last-month', 'this-year', 'custom'],
}
export const UTILITIES_PERIODS: PeriodChoice = {
  fallback: 'this-year',
  allowed: ['this-month', 'last-month', 'this-year', 'custom'],
}

export const CURRENCIES = ['MXN', 'USD'] as const
export type Currency = (typeof CURRENCIES)[number]

export const UTILITY_VIEWS = ['totals', 'tracker'] as const
export type UtilityView = (typeof UTILITY_VIEWS)[number]

export type StatementFilters = PeriodFilter & {
  property: string
  currency: Currency | ''
}
export type UtilitiesFilters = StatementFilters & { view: UtilityView }

const oneOf = <T extends string>(value: string | null, allowed: readonly T[]): T | '' =>
  allowed.includes(value as T) ? (value as T) : ''

export function parseStatementFilters(params: URLSearchParams): StatementFilters {
  return {
    ...readPeriod(params, STATEMENT_PERIODS),
    property: params.get('property') ?? '',
    currency: oneOf(params.get('currency'), CURRENCIES),
  }
}

export function serializeStatementFilters(filters: StatementFilters): string {
  const params = new URLSearchParams()
  writePeriod(params, filters, STATEMENT_PERIODS)
  if (filters.property) params.set('property', filters.property)
  if (filters.currency) params.set('currency', filters.currency)
  return params.toString()
}

export function parseUtilitiesFilters(params: URLSearchParams): UtilitiesFilters {
  return {
    ...readPeriod(params, UTILITIES_PERIODS),
    property: params.get('property') ?? '',
    currency: oneOf(params.get('currency'), CURRENCIES),
    view: oneOf(params.get('view'), UTILITY_VIEWS) || 'totals',
  }
}

export function serializeUtilitiesFilters(filters: UtilitiesFilters): string {
  const params = new URLSearchParams()
  writePeriod(params, filters, UTILITIES_PERIODS)
  if (filters.property) params.set('property', filters.property)
  if (filters.currency) params.set('currency', filters.currency)
  if (filters.view !== 'totals') params.set('view', filters.view)
  return params.toString()
}

/** The days a report covers: every period a report offers has an end. */
export function reportRange(filters: PeriodFilter, today: string, choice: PeriodChoice) {
  const range =
    getRange(filters.period, today, filters.period === 'custom' ? filters : undefined) ??
    getRange(choice.fallback, today)
  return { start: range?.from ?? today, end: range?.to ?? today }
}

/** `?start=…&end=…`: the query a download link carries, with the currency if chosen. */
export function toQueryString(
  query: Record<string, string | string[] | undefined>,
): string {
  const params = new URLSearchParams()
  for (const [key, value] of Object.entries(query)) {
    for (const one of Array.isArray(value) ? value : value ? [value] : []) {
      params.append(key, one)
    }
  }
  return params.toString()
}
