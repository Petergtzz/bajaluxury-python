import type { PaymentMethod, TransactionType } from '@/lib/api/types'

import { DEFAULT_PERIOD, getRange, type Period, PERIODS, type Range } from './period'

/** What narrows the ledger, as the address carries it. */
export type LedgerFilters = {
  period: Period
  from: string
  to: string
  property: string
  type: TransactionType | ''
  method: PaymentMethod | ''
  category: string
}

const TYPES: readonly TransactionType[] = ['income', 'expense']
const METHODS: readonly PaymentMethod[] = [
  'cash',
  'credit card',
  'debit card',
  'withdrawal',
  'check',
  'wire',
  'paypal',
]
const DATE = /^\d{4}-\d{2}-\d{2}$/

const oneOf = <T extends string>(value: string | null, allowed: readonly T[]): T | '' =>
  allowed.includes(value as T) ? (value as T) : ''

/** Filters from the address; anything unknown is left out, not trusted. */
export function parseFilters(params: URLSearchParams): LedgerFilters {
  const from = params.get('from') ?? ''
  const to = params.get('to') ?? ''
  const period = oneOf(params.get('period'), PERIODS) || DEFAULT_PERIOD
  const custom = period === 'custom' && DATE.test(from) && DATE.test(to) && from <= to
  return {
    period: period === 'custom' && !custom ? DEFAULT_PERIOD : period,
    from: custom ? from : '',
    to: custom ? to : '',
    property: params.get('property') ?? '',
    type: oneOf(params.get('type'), TYPES),
    method: oneOf(params.get('method'), METHODS),
    category: params.get('category') ?? '',
  }
}

/** The address for filters, leaving out whatever is at its default. */
export function serializeFilters(filters: LedgerFilters): string {
  const params = new URLSearchParams()
  if (filters.period !== DEFAULT_PERIOD) params.set('period', filters.period)
  if (filters.period === 'custom') {
    params.set('from', filters.from)
    params.set('to', filters.to)
  }
  for (const key of ['property', 'type', 'method', 'category'] as const) {
    if (filters[key]) params.set(key, filters[key])
  }
  return params.toString()
}

export const customRange = (filters: LedgerFilters): Range | undefined =>
  filters.period === 'custom' ? { from: filters.from, to: filters.to } : undefined

/** The API's query for filters, today being the company's today. */
export function toTransactionQuery(filters: LedgerFilters, today: string) {
  const range = getRange(filters.period, today, customRange(filters))
  return {
    ...(range && { start_date: range.from, end_date: range.to }),
    ...(filters.property && { property_id: filters.property }),
    ...(filters.type && { type: filters.type }),
    ...(filters.method && { payment_method: filters.method }),
    ...(filters.category && { category: filters.category }),
  }
}

export { METHODS }
